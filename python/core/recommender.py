"""Auto Recommendation: menyarankan analisis yang sesuai dengan dataset.

Setiap saran wajib menyebutkan kolom yang mendasarinya. Rekomendasi tanpa alasan
tidak bisa ditelusuri pengguna dan akan terbaca sebagai tebakan; dengan alasan,
pengguna bisa menilai sendiri apakah dugaan sistem tentang datanya benar.

Rekomendasi tidak pernah mengunci pilihan — seluruh analisis tetap dapat
dijalankan, yang disarankan hanya ditandai dan diurutkan lebih dulu.
"""

from __future__ import annotations

import pandas as pd

from core import loader

MAX_TARGET_CLASSES = 12
STRONG_CORRELATION = 0.4
OUTLIER_ALERT = 0.02
BASKET_LIFT = 1.4
BASKET_SUPPORT = 0.05


def characteristics(frame: pd.DataFrame) -> dict:
    numeric = loader.numeric_columns(frame)
    categorical = loader.categorical_columns(frame)
    datetimes = loader.datetime_columns(frame)
    identifiers = [name for name in frame.columns if loader.is_identifier(frame[name])]

    target_candidates = [
        name for name in categorical
        if 2 <= frame[name].nunique(dropna=True) <= MAX_TARGET_CLASSES
    ]

    # Kolom numerik yang berhubungan dengan kolom numerik lain lebih layak jadi
    # target regresi daripada kolom yang berdiri sendiri.
    strongest = {}

    if len(numeric) >= 2:
        matrix = frame[numeric].corr(numeric_only=True).abs()

        for name in numeric:
            others = matrix[name].drop(labels=[name], errors="ignore")
            strongest[name] = float(others.max()) if not others.empty else 0.0

    basket = [name for name in categorical if frame[name].nunique(dropna=True) <= 12]

    return {
        "row_count": int(len(frame)),
        "numeric": numeric,
        "categorical": categorical,
        "datetime": datetimes,
        "identifiers": identifiers,
        "target_candidates": sorted(
            target_candidates, key=lambda name: frame[name].nunique()
        ),
        "numeric_strength": strongest,
        "basket_columns": basket,
        "basket_lift": _basket_strength(frame, basket),
        "outlier_ratio": _outlier_ratio(frame, numeric),
    }


def _outlier_ratio(frame: pd.DataFrame, numeric: list) -> float:
    if not numeric or frame.empty:
        return 0.0

    total = 0

    for name in numeric:
        values = frame[name].dropna()

        if values.empty:
            continue

        q1, q3 = values.quantile(0.25), values.quantile(0.75)
        iqr = q3 - q1
        total += int(((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).sum())

    return round(total / (len(numeric) * len(frame)), 6)


def _basket_strength(frame: pd.DataFrame, columns: list) -> float:
    """Seberapa kuat nilai antar kolom kategori muncul bersamaan.

    Tanpa ukuran ini, "data transaksional" hanya berarti "punya beberapa kolom
    kategori" — dan itu benar untuk hampir semua tabel, sehingga Association Rule
    akan disarankan di mana-mana. Yang menentukan sebenarnya adalah ada tidaknya
    pasangan nilai yang benar-benar berulang bersamaan.
    """
    if len(columns) < 2 or frame.empty:
        return 0.0

    total = len(frame)
    highest = 0.0

    for i, left in enumerate(columns):
        for right in columns[i + 1:]:
            pair = frame[[left, right]].dropna()

            if pair.empty:
                continue

            joint = pair.groupby([left, right], observed=True).size() / total
            left_share = pair[left].value_counts(normalize=True)
            right_share = pair[right].value_counts(normalize=True)

            for (left_value, right_value), support in joint.items():
                if support < BASKET_SUPPORT:
                    continue

                expected = left_share.get(left_value, 0) * right_share.get(right_value, 0)

                if expected > 0:
                    highest = max(highest, support / expected)

    return round(float(highest), 3)


def run(params: dict) -> dict:
    frame = loader.load(params)
    facts = characteristics(frame)
    suggestions = []

    targets = facts["target_candidates"]
    numeric_strength = facts["numeric_strength"]

    if targets:
        target = targets[0]
        classes = int(frame[target].nunique())
        suggestions.append({
            "key": "classification",
            "name": "Classification",
            "level": "high",
            "reason": f'Kolom "{target}" berisi {classes} kelas — cocok dijadikan target klasifikasi.',
            "suggested_target": target,
        })

    if numeric_strength:
        best = max(numeric_strength, key=numeric_strength.get)
        strength = numeric_strength[best]

        suggestions.append({
            "key": "regression",
            "name": "Regression",
            "level": "high" if strength >= STRONG_CORRELATION else "medium",
            "reason": (
                f'Kolom "{best}" berkorelasi {strength:.2f} dengan kolom numerik lain — '
                "nilainya dapat diprediksi."
                if strength >= STRONG_CORRELATION
                else f"Ada {len(facts['numeric'])} kolom numerik, tetapi korelasi antar kolom masih lemah."
            ),
            "suggested_target": best,
        })

    if facts["datetime"] and facts["numeric"]:
        suggestions.append({
            "key": "forecasting",
            "name": "Forecasting",
            "level": "high",
            "reason": (
                f'Kolom waktu "{facts["datetime"][0]}" tersedia, sehingga nilai numerik '
                "bisa dianalisis dan diproyeksikan sebagai deret waktu."
            ),
            "suggested_target": facts["numeric"][0],
        })

    if facts["identifiers"] and len(facts["basket_columns"]) >= 2 and facts["basket_lift"] >= BASKET_LIFT:
        suggestions.append({
            "key": "association",
            "name": "Association Rule",
            "level": "high",
            "reason": (
                f"Berbentuk transaksi: {len(facts['basket_columns'])} kolom item, dengan "
                f"pasangan nilai yang muncul bersama {facts['basket_lift']:.1f}× lebih sering "
                "daripada kebetulan."
            ),
        })

    ratio = facts["outlier_ratio"]
    suggestions.append({
        "key": "anomaly",
        "name": "Anomaly Detection",
        "level": "high" if ratio >= OUTLIER_ALERT else "medium",
        "reason": (
            f"{ratio * 100:.1f}% nilai numerik berada di luar batas wajar — "
            "jumlah nilai ekstremnya menonjol."
            if ratio >= OUTLIER_ALERT
            else f"Nilai ekstrem hanya {ratio * 100:.1f}% dari data, anomali kemungkinan sedikit."
        ),
    })

    if not targets:
        suggestions.append({
            "key": "clustering",
            "name": "Clustering",
            "level": "high",
            "reason": "Tidak ada kolom target yang jelas — pengelompokan tanpa label paling masuk akal.",
        })
    elif len(facts["numeric"]) >= 2:
        suggestions.append({
            "key": "clustering",
            "name": "Clustering",
            "level": "medium",
            "reason": (
                f"Ada {len(facts['numeric'])} kolom numerik yang bisa dikelompokkan "
                "sebagai segmentasi tambahan."
            ),
        })

    order = {"high": 0, "medium": 1}
    suggestions.sort(key=lambda item: order.get(item["level"], 2))

    return {
        "characteristics": {
            "row_count": facts["row_count"],
            "numeric_count": len(facts["numeric"]),
            "categorical_count": len(facts["categorical"]),
            "datetime_count": len(facts["datetime"]),
            "identifier_count": len(facts["identifiers"]),
            "outlier_ratio": facts["outlier_ratio"],
            "basket_lift": facts["basket_lift"],
            "target_candidates": targets[:5],
            "is_transactional": bool(
                facts["identifiers"]
                and len(facts["basket_columns"]) >= 2
                and facts["basket_lift"] >= BASKET_LIFT
            ),
        },
        "recommendations": suggestions,
    }
