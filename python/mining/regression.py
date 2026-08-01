"""Regression untuk halaman Data Mining.

Pembungkus tipis di atas `ml.supervised`, sama seperti modul classification,
supaya metrik regresi konsisten di seluruh aplikasi.
"""

from __future__ import annotations

from core import loader
from core.io import EngineError
from ml import automl, supervised


def run(params: dict) -> dict:
    frame = loader.load(params)
    target = params.get("target") or _auto_target(frame)

    if not target:
        raise EngineError("Tidak ada kolom numerik yang layak dijadikan target regresi.")

    features = params.get("features") or _auto_features(frame, target)
    bundle = supervised.train(frame, {**params, "target": target, "features": features})
    bundle["data"]["target"] = target

    return automl._serialize(bundle)


def _auto_target(frame):
    """Kolom numerik yang paling berhubungan dengan kolom numerik lain.

    Kolom yang berdiri sendiri tidak bisa diprediksi dari kolom mana pun, jadi
    memilihnya sebagai target hanya akan menghasilkan model dengan R² mendekati nol.
    """
    numeric = loader.numeric_columns(frame)

    if len(numeric) < 2:
        return numeric[0] if numeric else None

    matrix = frame[numeric].corr(numeric_only=True).abs()
    strength = {
        name: float(matrix[name].drop(labels=[name], errors="ignore").max())
        for name in numeric
    }

    return max(strength, key=strength.get)


def _auto_features(frame, target: str) -> list:
    return [
        name for name in frame.columns
        if name != target
        and not loader.is_identifier(frame[name])
        and loader.column_kind(frame[name]) != "datetime"
    ]
