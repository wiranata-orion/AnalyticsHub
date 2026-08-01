"""Classification untuk halaman Data Mining.

Pembungkus tipis di atas `ml.supervised` agar hasil klasifikasi di Data Mining
dihitung dengan cara yang persis sama dengan halaman Machine Learning. Bedanya
hanya pada target dan fitur yang dipilihkan otomatis bila pengguna belum memilih.
"""

from __future__ import annotations

from core import loader
from core.io import EngineError
from ml import automl, supervised


def run(params: dict) -> dict:
    frame = loader.load(params)
    target = params.get("target") or _auto_target(frame)

    if not target:
        raise EngineError(
            "Tidak ada kolom kategorikal yang layak dijadikan target klasifikasi."
        )

    features = params.get("features") or _auto_features(frame, target)
    bundle = supervised.train(frame, {**params, "target": target, "features": features})
    bundle["data"]["target"] = target

    return automl._serialize(bundle)


def _auto_target(frame):
    candidates = [
        name for name in loader.categorical_columns(frame)
        if 2 <= frame[name].nunique(dropna=True) <= 12
    ]

    return min(candidates, key=lambda name: frame[name].nunique()) if candidates else None


def _auto_features(frame, target: str) -> list:
    return [
        name for name in frame.columns
        if name != target
        and not loader.is_identifier(frame[name])
        and loader.column_kind(frame[name]) != "datetime"
    ]
