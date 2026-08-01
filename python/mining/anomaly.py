"""Anomaly Detection: menandai baris yang menyimpang dari pola umum."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core import loader
from core.io import EngineError

MAX_COLUMNS = 8


def run(params: dict) -> dict:
    from sklearn.ensemble import IsolationForest
    from sklearn.neighbors import LocalOutlierFactor
    from sklearn.preprocessing import StandardScaler

    frame = loader.load(params)
    columns = params.get("columns") or loader.numeric_columns(frame)[:MAX_COLUMNS]

    if not columns:
        raise EngineError("Deteksi anomali butuh minimal satu kolom numerik.")

    subset = frame[columns].dropna()

    if len(subset) < 20:
        raise EngineError("Baris lengkap terlalu sedikit untuk deteksi anomali (minimal 20).")

    scaled = StandardScaler().fit_transform(subset)
    contamination = float(params.get("contamination", 0.05))
    method = params.get("method", "isolation_forest")

    if method == "lof":
        model = LocalOutlierFactor(n_neighbors=min(20, len(subset) - 1), contamination=contamination)
        flags = model.fit_predict(scaled)
        scores = -model.negative_outlier_factor_
    elif method == "iqr":
        # Batas Tukey per kolom: sederhana, dan alasannya paling mudah dijelaskan.
        flags = np.ones(len(subset))
        scores = np.zeros(len(subset))

        for index, name in enumerate(columns):
            values = subset[name]
            q1, q3 = values.quantile(0.25), values.quantile(0.75)
            iqr = q3 - q1
            outside = (values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)
            flags[outside.to_numpy()] = -1
            scores = np.maximum(scores, np.abs(scaled[:, index]))
    else:
        model = IsolationForest(contamination=contamination, random_state=42, n_estimators=200)
        flags = model.fit_predict(scaled)
        scores = -model.score_samples(scaled)

    is_anomaly = flags == -1
    count = int(is_anomaly.sum())

    # Kolom penyebab dicatat agar hasilnya bisa dijelaskan, bukan sekadar ditandai.
    causes = []

    for position in np.where(is_anomaly)[0]:
        deviations = np.abs(scaled[position])
        cause_index = int(np.argmax(deviations))
        causes.append({
            "row": int(subset.index[position]),
            "score": round(float(scores[position]), 4),
            "cause": columns[cause_index],
            "value": float(subset.iloc[position, cause_index]),
            "deviation": round(float(deviations[cause_index]), 2),
            "context": {
                name: float(subset.iloc[position][name]) for name in columns[:4]
            },
        })

    causes.sort(key=lambda item: item["score"], reverse=True)

    axes = columns[:2] if len(columns) >= 2 else [columns[0], columns[0]]

    return {
        "method": method,
        "columns": columns,
        "checked": int(len(subset)),
        "count": count,
        "ratio": round(count / len(subset), 4),
        "top": causes[:20],
        "axes": axes,
        "series": [
            {
                "label": "Normal",
                "data": [
                    {"x": float(row[0]), "y": float(row[1])}
                    for row in subset.loc[~is_anomaly, axes].itertuples(index=False)
                ],
            },
            {
                "label": "Anomali",
                "data": [
                    {"x": float(row[0]), "y": float(row[1])}
                    for row in subset.loc[is_anomaly, axes].itertuples(index=False)
                ],
            },
        ],
        "interpretation": (
            f"{count} dari {len(subset)} baris ({count / len(subset) * 100:.1f}%) "
            "menyimpang dari pola umum"
            + (f', paling sering dipicu kolom "{causes[0]["cause"]}".' if causes else ".")
        ),
    }
