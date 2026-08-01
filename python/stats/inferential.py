"""Statistik inferensial: menguji dugaan, bukan sekadar mendeskripsikan.

Tujuh uji yang diminta halaman Statistical Analysis:

    t_test          beda rata-rata dua kelompok (parametrik)
    anova           beda rata-rata tiga kelompok atau lebih (parametrik)
    mann_whitney    padanan t-test saat sebaran tidak normal
    kruskal         padanan ANOVA saat sebaran tidak normal
    chi_square      keterkaitan dua kolom kategorikal
    pearson         korelasi linear dua kolom numerik
    spearman        korelasi peringkat, tahan terhadap pencilan

Setiap hasil menyertakan kesimpulan dalam kalimat biasa. Nilai p sendiri sering
disalahartikan; menuliskan "berbeda bermakna pada taraf 5%" jauh lebih sulit
disalahpahami daripada menampilkan 0,032 saja.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from core import loader
from core.io import EngineError, require

ALPHA = 0.05


def run(params: dict) -> dict:
    frame = loader.load(params)
    (test,) = require(params, "test")

    handlers = {
        "t_test": _t_test,
        "anova": _anova,
        "mann_whitney": _mann_whitney,
        "kruskal": _kruskal,
        "chi_square": _chi_square,
        "pearson": _pearson,
        "spearman": _spearman,
    }

    handler = handlers.get(test)

    if handler is None:
        raise EngineError(
            f"Uji '{test}' tidak dikenal. Pilihan: " + ", ".join(sorted(handlers))
        )

    alpha = float(params.get("alpha", ALPHA))
    result = handler(frame, params, alpha)

    return {"test": test, "alpha": alpha, **result}


def _verdict(p_value: float, alpha: float, positive: str, negative: str) -> dict:
    significant = bool(p_value < alpha)

    return {
        "significant": significant,
        "conclusion": positive if significant else negative,
    }


def _groups(frame: pd.DataFrame, value_column: str, group_column: str) -> list:
    if value_column not in frame.columns:
        raise EngineError(f'Kolom nilai "{value_column}" tidak ada.')

    if group_column not in frame.columns:
        raise EngineError(f'Kolom kelompok "{group_column}" tidak ada.')

    pair = frame[[value_column, group_column]].dropna()

    if not pd.api.types.is_numeric_dtype(pair[value_column]):
        raise EngineError(f'Kolom "{value_column}" harus numerik untuk uji ini.')

    groups = [
        {"label": str(label), "values": values[value_column].to_numpy()}
        for label, values in pair.groupby(group_column, observed=True)
        if len(values) >= 2
    ]

    if len(groups) < 2:
        raise EngineError(
            f'Kolom "{group_column}" harus punya minimal dua kelompok dengan '
            "sedikitnya dua baris masing-masing."
        )

    return groups


def _describe_groups(groups: list) -> list:
    return [
        {
            "label": group["label"],
            "n": int(len(group["values"])),
            "mean": float(np.mean(group["values"])),
            "median": float(np.median(group["values"])),
            "std": float(np.std(group["values"], ddof=1)) if len(group["values"]) > 1 else 0.0,
        }
        for group in groups
    ]


def _t_test(frame: pd.DataFrame, params: dict, alpha: float) -> dict:
    value_column, group_column = require(params, "value", "group")
    groups = _groups(frame, value_column, group_column)

    if len(groups) != 2:
        raise EngineError(
            f'Kolom "{group_column}" punya {len(groups)} kelompok. '
            "T-test hanya untuk dua kelompok — gunakan ANOVA untuk lebih dari dua."
        )

    first, second = groups[0]["values"], groups[1]["values"]

    # Uji Levene menentukan apakah asumsi ragam sama terpenuhi; bila tidak,
    # dipakai Welch yang tidak mensyaratkannya.
    _, levene_p = stats.levene(first, second)
    equal_variance = bool(levene_p > alpha)
    statistic, p_value = stats.ttest_ind(first, second, equal_var=equal_variance)

    # Cohen's d: seberapa besar bedanya, bukan sekadar apakah berbeda.
    pooled = np.sqrt((np.var(first, ddof=1) + np.var(second, ddof=1)) / 2)
    cohens_d = float((np.mean(first) - np.mean(second)) / pooled) if pooled else 0.0

    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "equal_variance": equal_variance,
        "variant": "Student" if equal_variance else "Welch",
        "effect_size": {"name": "Cohen's d", "value": cohens_d, "magnitude": _effect_words(abs(cohens_d))},
        "groups": _describe_groups(groups),
        **_verdict(
            float(p_value), alpha,
            f'Rata-rata "{value_column}" berbeda bermakna antara {groups[0]["label"]} dan {groups[1]["label"]}.',
            f'Tidak ada bukti cukup bahwa rata-rata "{value_column}" berbeda antar kedua kelompok.',
        ),
    }


def _effect_words(value: float) -> str:
    if value >= 0.8:
        return "besar"
    if value >= 0.5:
        return "sedang"
    if value >= 0.2:
        return "kecil"

    return "sangat kecil"


def _anova(frame: pd.DataFrame, params: dict, alpha: float) -> dict:
    value_column, group_column = require(params, "value", "group")
    groups = _groups(frame, value_column, group_column)
    statistic, p_value = stats.f_oneway(*[group["values"] for group in groups])

    # Eta kuadrat: porsi keragaman nilai yang dijelaskan oleh pengelompokan.
    combined = np.concatenate([group["values"] for group in groups])
    grand_mean = combined.mean()
    between = sum(
        len(group["values"]) * (group["values"].mean() - grand_mean) ** 2
        for group in groups
    )
    total = ((combined - grand_mean) ** 2).sum()
    eta_squared = float(between / total) if total else 0.0

    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "group_count": len(groups),
        "effect_size": {"name": "Eta²", "value": eta_squared, "magnitude": _effect_words(eta_squared * 2)},
        "groups": _describe_groups(groups),
        **_verdict(
            float(p_value), alpha,
            f'Minimal satu kelompok "{group_column}" punya rata-rata "{value_column}" yang berbeda bermakna.',
            f'Tidak ada bukti cukup bahwa rata-rata "{value_column}" berbeda antar kelompok.',
        ),
    }


def _mann_whitney(frame: pd.DataFrame, params: dict, alpha: float) -> dict:
    value_column, group_column = require(params, "value", "group")
    groups = _groups(frame, value_column, group_column)

    if len(groups) != 2:
        raise EngineError("Mann-Whitney hanya untuk dua kelompok.")

    statistic, p_value = stats.mannwhitneyu(
        groups[0]["values"], groups[1]["values"], alternative="two-sided"
    )

    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "groups": _describe_groups(groups),
        "note": "Uji non-parametrik: tidak mensyaratkan sebaran normal.",
        **_verdict(
            float(p_value), alpha,
            f'Sebaran "{value_column}" berbeda bermakna antara {groups[0]["label"]} dan {groups[1]["label"]}.',
            f'Tidak ada bukti cukup bahwa sebaran "{value_column}" berbeda antar kedua kelompok.',
        ),
    }


def _kruskal(frame: pd.DataFrame, params: dict, alpha: float) -> dict:
    value_column, group_column = require(params, "value", "group")
    groups = _groups(frame, value_column, group_column)
    statistic, p_value = stats.kruskal(*[group["values"] for group in groups])

    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "group_count": len(groups),
        "groups": _describe_groups(groups),
        "note": "Uji non-parametrik: padanan ANOVA saat sebaran tidak normal.",
        **_verdict(
            float(p_value), alpha,
            f'Minimal satu kelompok "{group_column}" punya sebaran "{value_column}" yang berbeda bermakna.',
            f'Tidak ada bukti cukup bahwa sebaran "{value_column}" berbeda antar kelompok.',
        ),
    }


def _chi_square(frame: pd.DataFrame, params: dict, alpha: float) -> dict:
    x_column, y_column = require(params, "x", "y")

    for column in (x_column, y_column):
        if column not in frame.columns:
            raise EngineError(f'Kolom "{column}" tidak ada pada dataset ini.')

    pair = frame[[x_column, y_column]].dropna()
    table = pd.crosstab(pair[x_column], pair[y_column])

    if table.shape[0] < 2 or table.shape[1] < 2:
        raise EngineError("Chi-square butuh kedua kolom punya minimal dua kategori.")

    statistic, p_value, dof, expected = stats.chi2_contingency(table)

    n = table.to_numpy().sum()
    min_dim = min(table.shape) - 1
    cramers_v = float(np.sqrt(statistic / (n * min_dim))) if n and min_dim else 0.0

    # Chi-square tidak sah bila terlalu banyak sel berfrekuensi harapan kecil.
    small_cells = int((expected < 5).sum())
    warning = (
        f"{small_cells} sel punya frekuensi harapan di bawah 5 — hasilnya perlu dibaca hati-hati."
        if small_cells > 0.2 * expected.size else None
    )

    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "degrees_of_freedom": int(dof),
        "effect_size": {"name": "Cramér's V", "value": cramers_v, "magnitude": _effect_words(cramers_v * 2)},
        "table": {
            "rows": [str(index) for index in table.index],
            "columns": [str(column) for column in table.columns],
            "observed": table.to_numpy().tolist(),
            "expected": [[round(float(value), 2) for value in row] for row in expected],
        },
        "warning": warning,
        **_verdict(
            float(p_value), alpha,
            f'"{x_column}" dan "{y_column}" saling terkait secara bermakna.',
            f'Tidak ada bukti cukup bahwa "{x_column}" dan "{y_column}" saling terkait.',
        ),
    }


def _correlation(frame: pd.DataFrame, params: dict, alpha: float, method: str) -> dict:
    x_column, y_column = require(params, "x", "y")

    for column in (x_column, y_column):
        if column not in frame.columns:
            raise EngineError(f'Kolom "{column}" tidak ada pada dataset ini.')

    pair = frame[[x_column, y_column]].dropna()

    for column in (x_column, y_column):
        if not pd.api.types.is_numeric_dtype(pair[column]):
            raise EngineError(f'Kolom "{column}" harus numerik untuk uji korelasi.')

    if len(pair) < 3:
        raise EngineError("Butuh minimal tiga baris yang kedua kolomnya terisi.")

    if method == "pearson":
        coefficient, p_value = stats.pearsonr(pair[x_column], pair[y_column])
        note = "Mengukur hubungan linear; peka terhadap pencilan."
    else:
        coefficient, p_value = stats.spearmanr(pair[x_column], pair[y_column])
        note = "Mengukur hubungan berdasarkan peringkat; tahan terhadap pencilan."

    strength = abs(coefficient)
    label = "kuat" if strength >= 0.7 else "sedang" if strength >= 0.4 else "lemah"
    direction = "positif" if coefficient >= 0 else "negatif"

    return {
        "coefficient": float(coefficient),
        "p_value": float(p_value),
        "n": int(len(pair)),
        "note": note,
        "points": [
            {"x": float(row[0]), "y": float(row[1])}
            for row in loader.sample(pair, 2000).itertuples(index=False)
        ],
        **_verdict(
            float(p_value), alpha,
            f'Terdapat hubungan {label} dan {direction} antara "{x_column}" dan "{y_column}" (r = {coefficient:.2f}).',
            f'Tidak ada bukti cukup adanya hubungan antara "{x_column}" dan "{y_column}".',
        ),
    }


def _pearson(frame: pd.DataFrame, params: dict, alpha: float) -> dict:
    return _correlation(frame, params, alpha, "pearson")


def _spearman(frame: pd.DataFrame, params: dict, alpha: float) -> dict:
    return _correlation(frame, params, alpha, "spearman")
