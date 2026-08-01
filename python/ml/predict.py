"""Prediksi memakai model yang sudah dilatih."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd

from core import loader
from core.io import EngineError
from ml import supervised


def run(params: dict) -> dict:
    artifact_path = params.get("artifact_path")

    if not artifact_path:
        raise EngineError("Model belum disimpan sehingga tidak bisa dipakai memprediksi.")

    bundle = supervised.load_artifact(artifact_path)
    frame = loader.load(params)

    features = bundle["features"]
    missing = [name for name in features if name not in frame.columns]

    if missing:
        # Mengisi kolom yang hilang dengan nilai default akan menghasilkan
        # prediksi yang tidak bisa dipertanggungjawabkan; lebih baik menolak.
        raise EngineError(
            "Dataset ini tidak memiliki kolom "
            + ", ".join(f'"{name}"' for name in missing)
            + " yang dipakai model."
        )

    subset = frame[features].dropna()

    if subset.empty:
        raise EngineError("Tidak ada baris dengan seluruh kolom fitur terisi.")

    matrix = pd.DataFrame(index=subset.index)
    encoders = bundle.get("encoders") or {}

    for name in features:
        column = subset[name]

        if name in encoders:
            mapping = encoders[name]
            # Nilai yang tak pernah dilihat saat pelatihan diberi -1: model tetap
            # bisa memprediksi, dan jumlahnya dilaporkan agar hasilnya dinilai
            # dengan tepat.
            matrix[name] = column.astype(str).map(mapping).fillna(-1).astype(int)
        elif loader.column_kind(column) == "datetime":
            matrix[name] = pd.to_datetime(column).astype("int64") // 10**9
        else:
            matrix[name] = pd.to_numeric(column, errors="coerce").fillna(0).astype(float)

    unseen = int(sum((matrix[name] == -1).sum() for name in encoders if name in matrix))

    started = time.perf_counter()
    predictions = bundle["model"].predict(matrix)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    classes = bundle.get("classes")
    task = bundle.get("task", "classification")

    if task == "classification" and classes:
        labels = [classes[int(value)] if 0 <= int(value) < len(classes) else str(value)
                  for value in predictions]
        counts = pd.Series(labels).value_counts()

        result = {
            "task": "classification",
            "total": int(len(labels)),
            "skipped": int(len(frame) - len(subset)),
            "unseen_categories": unseen,
            "distribution": [
                {
                    "label": str(index),
                    "count": int(count),
                    "share": round(float(count) / len(labels) * 100, 2),
                }
                for index, count in counts.items()
            ],
            "sample": _sample(subset, features, labels),
        }
    else:
        values = np.asarray(predictions, dtype=float)
        result = {
            "task": "regression",
            "total": int(len(values)),
            "skipped": int(len(frame) - len(subset)),
            "unseen_categories": unseen,
            "summary": {
                "mean": float(values.mean()),
                "median": float(np.median(values)),
                "min": float(values.min()),
                "max": float(values.max()),
                "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
            },
            "sample": _sample(subset, features, [round(float(value), 4) for value in values]),
        }

    result["prediction_time_ms"] = elapsed_ms

    return result


def _sample(subset: pd.DataFrame, features: list, predictions: list, limit: int = 15) -> list:
    return [
        {
            "id": position + 1,
            "features": " · ".join(
                f"{name}: {subset.iloc[position][name]}" for name in features[:5]
            ),
            "prediction": predictions[position],
        }
        for position in range(min(limit, len(subset)))
    ]
