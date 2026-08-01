"""Exploratory Data Analysis.

Delapan sudut pandang terhadap dataset yang sama, dipakai sebelum Data Mining
dan Machine Learning:

    univariate           satu kolom sendirian
    bivariate            hubungan dua kolom
    multivariate         beberapa kolom sekaligus
    correlation          kekuatan hubungan antar kolom numerik
    distribution         bentuk sebaran dan normalitasnya
    pairplot             matriks scatter antar kolom numerik
    missing_pattern      pola kekosongan, bukan sekadar jumlahnya
    feature_relationship kekuatan setiap fitur terhadap satu target

Semua mengembalikan data mentah (angka), bukan gambar. Penggambarannya
dilakukan Chart.js di frontend supaya grafiknya interaktif, mengikuti tema
terang/gelap, dan tetap bisa dibaca sebagai tabel.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from core import loader, profiler
from core.io import EngineError, require

# Batas baris untuk analisis yang biayanya kuadratik terhadap jumlah baris.
PAIRPLOT_ROWS = 2_000
PAIRPLOT_COLUMNS = 5


def _frame(params: dict) -> pd.DataFrame:
    return loader.load(params)


def _need(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        raise EngineError(f'Kolom "{column}" tidak ada pada dataset ini.')

    return frame[column]


# ---------------------------------------------------------------------------
# Univariate
# ---------------------------------------------------------------------------

def univariate(params: dict) -> dict:
    frame = _frame(params)
    column = params.get("column") or (loader.numeric_columns(frame) or list(frame.columns))[0]
    series = _need(frame, column)
    kind = loader.column_kind(series)
    values = series.dropna()

    if values.empty:
        raise EngineError(f'Kolom "{column}" seluruhnya kosong.')

    result = {
        "column": column,
        "type": kind,
        "count": int(len(values)),
        "missing": int(series.isna().sum()),
        "unique": int(values.nunique()),
    }

    if kind in ("integer", "float"):
        counts, edges = np.histogram(values, bins=min(20, max(5, int(np.sqrt(len(values))))))
        q1, q3 = float(values.quantile(0.25)), float(values.quantile(0.75))
        iqr = q3 - q1

        result.update({
            "summary": {
                "mean": float(values.mean()),
                "median": float(values.median()),
                "std": float(values.std()) if len(values) > 1 else 0.0,
                "min": float(values.min()),
                "max": float(values.max()),
                "q1": q1,
                "q3": q3,
                "iqr": float(iqr),
                "skewness": float(values.skew()) if len(values) > 2 else None,
                "kurtosis": float(values.kurtosis()) if len(values) > 3 else None,
            },
            "histogram": {
                "labels": [
                    f"{edges[i]:.2f}–{edges[i + 1]:.2f}" for i in range(len(edges) - 1)
                ],
                "counts": [int(item) for item in counts],
            },
            "boxplot": {
                "min": float(values.min()),
                "q1": q1,
                "median": float(values.median()),
                "q3": q3,
                "max": float(values.max()),
                "lower_fence": float(max(values.min(), q1 - 1.5 * iqr)),
                "upper_fence": float(min(values.max(), q3 + 1.5 * iqr)),
                "outlier_count": int(
                    ((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).sum()
                ),
            },
        })
    else:
        counts = values.astype(str).value_counts().head(20)
        result.update({
            "frequency": {
                "labels": [str(index) for index in counts.index],
                "counts": [int(item) for item in counts.values],
                "shares": [round(float(item) / len(values) * 100, 2) for item in counts.values],
            },
            "mode": str(values.mode().iloc[0]) if not values.mode().empty else None,
        })

    return result


# ---------------------------------------------------------------------------
# Bivariate
# ---------------------------------------------------------------------------

def bivariate(params: dict) -> dict:
    frame = _frame(params)
    x_column, y_column = require(params, "x", "y")

    x = _need(frame, x_column)
    y = _need(frame, y_column)
    x_kind, y_kind = loader.column_kind(x), loader.column_kind(y)
    numeric = ("integer", "float")

    pair = frame[[x_column, y_column]].dropna()

    if pair.empty:
        raise EngineError("Tidak ada baris yang kedua kolomnya terisi.")

    # Numerik vs numerik -> scatter + korelasi + garis regresi.
    if x_kind in numeric and y_kind in numeric:
        pearson_r, pearson_p = stats.pearsonr(pair[x_column], pair[y_column])
        spearman_r, spearman_p = stats.spearmanr(pair[x_column], pair[y_column])
        slope, intercept = np.polyfit(pair[x_column], pair[y_column], 1)

        sampled = loader.sample(pair, PAIRPLOT_ROWS)

        return {
            "mode": "numeric_numeric",
            "x": x_column,
            "y": y_column,
            "points": [
                {"x": float(row[0]), "y": float(row[1])}
                for row in sampled.itertuples(index=False)
            ],
            "pearson": {"r": float(pearson_r), "p_value": float(pearson_p)},
            "spearman": {"r": float(spearman_r), "p_value": float(spearman_p)},
            "trend": {"slope": float(slope), "intercept": float(intercept)},
            "interpretation": _correlation_words(float(pearson_r)),
        }

    # Kategori vs numerik -> ringkasan per kelompok.
    if x_kind not in numeric and y_kind in numeric:
        grouped = pair.groupby(x_column, observed=True)[y_column]
        summary = grouped.agg(["count", "mean", "median", "std", "min", "max"])
        summary = summary.sort_values("mean", ascending=False).head(15)

        return {
            "mode": "category_numeric",
            "x": x_column,
            "y": y_column,
            "groups": [
                {
                    "label": str(index),
                    "count": int(row["count"]),
                    "mean": float(row["mean"]),
                    "median": float(row["median"]),
                    "std": None if pd.isna(row["std"]) else float(row["std"]),
                    "min": float(row["min"]),
                    "max": float(row["max"]),
                }
                for index, row in summary.iterrows()
            ],
        }

    if x_kind in numeric and y_kind not in numeric:
        return bivariate({**params, "x": y_column, "y": x_column})

    # Kategori vs kategori -> tabel kontingensi + Cramér's V.
    table = pd.crosstab(pair[x_column], pair[y_column])
    table = table.iloc[:12, :12]
    chi2, p_value = stats.chi2_contingency(table)[:2]
    n = table.to_numpy().sum()
    min_dim = min(table.shape) - 1
    cramers_v = float(np.sqrt(chi2 / (n * min_dim))) if n and min_dim > 0 else 0.0

    return {
        "mode": "category_category",
        "x": x_column,
        "y": y_column,
        "rows": [str(index) for index in table.index],
        "columns": [str(column) for column in table.columns],
        "matrix": table.to_numpy().tolist(),
        "chi_square": float(chi2),
        "p_value": float(p_value),
        "cramers_v": cramers_v,
        "interpretation": (
            f"Keterkaitan {'kuat' if cramers_v >= 0.3 else 'lemah'} "
            f"(Cramér's V {cramers_v:.2f})."
        ),
    }


def _correlation_words(value: float) -> str:
    strength = abs(value)
    arah = "positif" if value >= 0 else "negatif"

    if strength >= 0.7:
        label = "kuat"
    elif strength >= 0.4:
        label = "sedang"
    elif strength >= 0.2:
        label = "lemah"
    else:
        label = "hampir tidak ada"

    return f"Hubungan {label} dan {arah} (r = {value:.2f})."


# ---------------------------------------------------------------------------
# Multivariate
# ---------------------------------------------------------------------------

def multivariate(params: dict) -> dict:
    """Beberapa kolom sekaligus: PCA dua komponen, diwarnai kolom kategori."""
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    frame = _frame(params)
    columns = params.get("columns") or loader.numeric_columns(frame)[:6]

    if len(columns) < 2:
        raise EngineError("Analisis multivariat butuh minimal dua kolom numerik.")

    color = params.get("color")
    subset = frame[columns + ([color] if color and color in frame.columns else [])].dropna()

    if len(subset) < 3:
        raise EngineError("Baris lengkap terlalu sedikit untuk analisis multivariat.")

    sampled = loader.sample(subset, PAIRPLOT_ROWS)
    scaled = StandardScaler().fit_transform(sampled[columns])
    pca = PCA(n_components=2, random_state=42)
    points = pca.fit_transform(scaled)

    groups = {}

    for index, (x, y) in enumerate(points):
        label = str(sampled[color].iloc[index]) if color and color in sampled.columns else "Semua data"
        groups.setdefault(label, []).append({"x": float(x), "y": float(y)})

    return {
        "columns": columns,
        "color": color,
        "explained_variance": [float(value) for value in pca.explained_variance_ratio_],
        "total_explained": float(pca.explained_variance_ratio_.sum()),
        "loadings": [
            {
                "column": column,
                "pc1": float(pca.components_[0][index]),
                "pc2": float(pca.components_[1][index]),
            }
            for index, column in enumerate(columns)
        ],
        "series": [
            {"label": label, "data": data}
            for label, data in list(groups.items())[:8]
        ],
        "interpretation": (
            f"Dua komponen pertama menjelaskan "
            f"{pca.explained_variance_ratio_.sum() * 100:.1f}% keragaman data."
        ),
    }


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------

def correlation(params: dict) -> dict:
    frame = _frame(params)
    method = params.get("method", "pearson")

    if method not in ("pearson", "spearman", "kendall"):
        raise EngineError("Metode korelasi harus pearson, spearman, atau kendall.")

    columns = params.get("columns") or loader.numeric_columns(frame)[:12]

    if len(columns) < 2:
        raise EngineError("Analisis korelasi butuh minimal dua kolom numerik.")

    matrix = profiler.correlation_matrix(frame, columns, method)

    # Pasangan terkuat diangkat ke atas agar pengguna tidak perlu memindai
    # seluruh matriks untuk menemukan yang penting.
    pairs = []

    for i, left in enumerate(columns):
        for j, right in enumerate(columns):
            if j <= i:
                continue

            value = matrix["matrix"][i][j]
            pairs.append({
                "x": left,
                "y": right,
                "value": value,
                "strength": abs(value),
                "interpretation": _correlation_words(value),
            })

    pairs.sort(key=lambda item: item["strength"], reverse=True)

    return {**matrix, "top_pairs": pairs[:10]}


# ---------------------------------------------------------------------------
# Distribution
# ---------------------------------------------------------------------------

def distribution(params: dict) -> dict:
    """Bentuk sebaran tiap kolom numerik beserta uji normalitasnya."""
    frame = _frame(params)
    columns = params.get("columns") or loader.numeric_columns(frame)[:6]

    if not columns:
        raise EngineError("Tidak ada kolom numerik untuk dianalisis sebarannya.")

    results = []

    for column in columns:
        values = frame[column].dropna()

        if len(values) < 8:
            continue

        # Shapiro-Wilk paling kuat tetapi dibatasi 5000 sampel; di atas itu
        # dipakai D'Agostino yang tetap sah untuk sampel besar.
        if len(values) <= 5000:
            statistic, p_value = stats.shapiro(values)
            test_name = "Shapiro-Wilk"
        else:
            statistic, p_value = stats.normaltest(values)
            test_name = "D'Agostino-Pearson"

        skew = float(values.skew())
        counts, edges = np.histogram(values, bins=20)

        results.append({
            "column": column,
            "test": test_name,
            "statistic": float(statistic),
            "p_value": float(p_value),
            "is_normal": bool(p_value > 0.05),
            "skewness": skew,
            "kurtosis": float(values.kurtosis()),
            "shape": _shape_words(skew),
            "histogram": {
                "labels": [f"{edges[i]:.2f}" for i in range(len(edges) - 1)],
                "counts": [int(item) for item in counts],
            },
            "interpretation": (
                f"Sebaran {'mendekati normal' if p_value > 0.05 else 'tidak normal'} "
                f"(p = {p_value:.4f}), {_shape_words(skew).lower()}."
            ),
        })

    return {"columns": results}


def _shape_words(skew: float) -> str:
    if skew > 1:
        return "Miring kuat ke kanan"
    if skew > 0.5:
        return "Miring ke kanan"
    if skew < -1:
        return "Miring kuat ke kiri"
    if skew < -0.5:
        return "Miring ke kiri"

    return "Cukup simetris"


# ---------------------------------------------------------------------------
# Pair plot
# ---------------------------------------------------------------------------

def pairplot(params: dict) -> dict:
    frame = _frame(params)
    columns = (params.get("columns") or loader.numeric_columns(frame))[:PAIRPLOT_COLUMNS]

    if len(columns) < 2:
        raise EngineError("Pair plot butuh minimal dua kolom numerik.")

    color = params.get("color")
    needed = columns + ([color] if color and color in frame.columns else [])
    subset = loader.sample(frame[needed].dropna(), PAIRPLOT_ROWS)

    if subset.empty:
        raise EngineError("Tidak ada baris yang seluruh kolomnya terisi.")

    cells = []

    for row_column in columns:
        for col_column in columns:
            if row_column == col_column:
                counts, edges = np.histogram(subset[row_column], bins=15)
                cells.append({
                    "row": row_column,
                    "column": col_column,
                    "kind": "histogram",
                    "labels": [f"{edges[i]:.1f}" for i in range(len(edges) - 1)],
                    "counts": [int(item) for item in counts],
                })
                continue

            groups = {}

            for _, record in subset.iterrows():
                label = str(record[color]) if color and color in subset.columns else "Data"
                groups.setdefault(label, []).append({
                    "x": float(record[col_column]),
                    "y": float(record[row_column]),
                })

            cells.append({
                "row": row_column,
                "column": col_column,
                "kind": "scatter",
                "correlation": float(subset[row_column].corr(subset[col_column])),
                "series": [
                    {"label": label, "data": data}
                    for label, data in list(groups.items())[:3]
                ],
            })

    return {"columns": columns, "color": color, "cells": cells, "sampled_rows": int(len(subset))}


# ---------------------------------------------------------------------------
# Missing pattern
# ---------------------------------------------------------------------------

def missing_pattern(params: dict) -> dict:
    """Pola kekosongan, bukan sekadar jumlahnya.

    Yang menentukan cara penanganan bukan berapa banyak yang kosong, melainkan
    apakah kekosongan itu muncul bersamaan di beberapa kolom — pola begitu
    biasanya menandakan satu proses pengumpulan data yang gagal, bukan kebetulan.
    """
    frame = _frame(params)
    total = len(frame)

    per_column = [
        {
            "column": str(name),
            "missing": int(frame[name].isna().sum()),
            "percent": round(float(frame[name].isna().mean() * 100), 2),
        }
        for name in frame.columns
    ]
    per_column.sort(key=lambda item: item["missing"], reverse=True)

    affected = [item["column"] for item in per_column if item["missing"] > 0]

    # Kombinasi kolom-kosong yang paling sering berulang.
    combinations = []

    if affected:
        mask = frame[affected].isna()
        signature = mask.apply(
            lambda row: ", ".join([column for column in affected if row[column]]) or "(lengkap)",
            axis=1,
        )
        counts = signature.value_counts().head(10)
        combinations = [
            {
                "pattern": str(index),
                "rows": int(count),
                "share": round(float(count) / total * 100, 2),
            }
            for index, count in counts.items()
        ]

    # Korelasi antar penanda kosong: nilai tinggi = dua kolom kosong bersamaan.
    correlation_pairs = []

    if len(affected) >= 2:
        indicator = frame[affected].isna().astype(int)
        matrix = indicator.corr()

        for i, left in enumerate(affected):
            for right in affected[i + 1:]:
                value = matrix.loc[left, right]

                if pd.notna(value) and abs(value) >= 0.3:
                    correlation_pairs.append({
                        "x": left,
                        "y": right,
                        "value": round(float(value), 3),
                    })

        correlation_pairs.sort(key=lambda item: abs(item["value"]), reverse=True)

    complete_rows = int(frame.dropna().shape[0])

    return {
        "row_count": total,
        "complete_rows": complete_rows,
        "complete_percent": round(complete_rows / total * 100, 2) if total else 0.0,
        "per_column": per_column,
        "combinations": combinations,
        "correlated_missing": correlation_pairs[:10],
        "interpretation": (
            f"{complete_rows} dari {total} baris terisi lengkap"
            + (
                f". Kekosongan pada {correlation_pairs[0]['x']} dan "
                f"{correlation_pairs[0]['y']} cenderung terjadi bersamaan."
                if correlation_pairs
                else "."
            )
        ),
    }


# ---------------------------------------------------------------------------
# Feature relationship
# ---------------------------------------------------------------------------

def feature_relationship(params: dict) -> dict:
    """Kekuatan setiap kolom terhadap satu target.

    Memakai mutual information: tidak seperti korelasi, ukuran ini menangkap
    hubungan non-linear dan bekerja untuk target kategorikal maupun numerik —
    jadi satu halaman cukup untuk kedua jenis target.
    """
    from sklearn.feature_selection import mutual_info_classif, mutual_info_regression
    from sklearn.preprocessing import LabelEncoder

    frame = _frame(params)
    (target,) = require(params, "target")

    if target not in frame.columns:
        raise EngineError(f'Kolom target "{target}" tidak ada pada dataset ini.')

    candidates = [
        name for name in frame.columns
        if name != target and not loader.is_identifier(frame[name])
        and loader.column_kind(frame[name]) != "datetime"
    ]

    if not candidates:
        raise EngineError("Tidak ada kolom lain yang bisa dibandingkan dengan target.")

    subset = frame[candidates + [target]].dropna()

    if len(subset) < 10:
        raise EngineError("Baris lengkap terlalu sedikit untuk mengukur hubungan fitur.")

    encoded = pd.DataFrame(index=subset.index)

    for name in candidates:
        column = subset[name]

        if loader.column_kind(column) in ("integer", "float"):
            encoded[name] = column
        else:
            encoded[name] = LabelEncoder().fit_transform(column.astype(str))

    target_kind = loader.column_kind(subset[target])
    is_classification = target_kind not in ("integer", "float")

    if is_classification:
        y = LabelEncoder().fit_transform(subset[target].astype(str))
        scores = mutual_info_classif(encoded, y, random_state=42)
    else:
        y = subset[target]
        scores = mutual_info_regression(encoded, y, random_state=42)

    total = float(scores.sum()) or 1.0
    features = sorted(
        [
            {
                "feature": name,
                "score": float(score),
                "share": round(float(score) / total * 100, 2),
                "type": loader.column_kind(subset[name]),
            }
            for name, score in zip(candidates, scores)
        ],
        key=lambda item: item["score"],
        reverse=True,
    )

    strongest = features[0] if features else None

    return {
        "target": target,
        "task": "classification" if is_classification else "regression",
        "features": features,
        "interpretation": (
            f'Kolom "{strongest["feature"]}" paling berhubungan dengan "{target}" '
            f"({strongest['share']:.1f}% dari total kekuatan hubungan)."
            if strongest else ""
        ),
    }
