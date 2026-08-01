"""Feature Engineering: menyiapkan kolom agar siap dipakai model.

Hasilnya disimpan sebagai berkas terpisah (feature set), bukan menimpa dataset
asli, karena satu dataset bisa melahirkan beberapa versi fitur — misalnya satu
memakai one-hot dan satu memakai label encoding — dan keduanya perlu bisa
dibandingkan di halaman Machine Learning.

Transformasi dijalankan berurutan sesuai daftar `steps` yang dikirim, dan urutan
itu ikut disimpan supaya hasilnya dapat ditelusuri serta diulang.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from core import loader
from core.io import EngineError, require


def _target_columns(frame: pd.DataFrame, step: dict, default: list) -> list:
    columns = step.get("columns") or default

    return [name for name in columns if name in frame.columns]


def _label_encoding(frame: pd.DataFrame, step: dict) -> tuple:
    from sklearn.preprocessing import LabelEncoder

    columns = _target_columns(frame, step, loader.categorical_columns(frame))
    mapping = {}

    for name in columns:
        encoder = LabelEncoder()
        filled = frame[name].astype(str).fillna("(kosong)")
        frame[name] = encoder.fit_transform(filled)
        mapping[name] = {
            str(label): int(code)
            for label, code in zip(encoder.classes_, range(len(encoder.classes_)))
        }

    return frame, {"columns": columns, "mapping": mapping}


def _one_hot(frame: pd.DataFrame, step: dict) -> tuple:
    columns = _target_columns(frame, step, loader.categorical_columns(frame, max_unique=20))

    if not columns:
        return frame, {"columns": [], "created": []}

    before = set(frame.columns)
    # drop_first menghindari kolom yang bisa disimpulkan dari sisanya, yang
    # membuat regresi linear tidak stabil karena kolinearitas sempurna.
    frame = pd.get_dummies(
        frame, columns=columns, drop_first=bool(step.get("drop_first", True)), dtype=int
    )
    created = sorted(set(frame.columns) - before)

    return frame, {"columns": columns, "created": created}


def _scale(frame: pd.DataFrame, step: dict, kind: str) -> tuple:
    from sklearn.preprocessing import MinMaxScaler, Normalizer, StandardScaler

    columns = _target_columns(frame, step, loader.numeric_columns(frame))

    if not columns:
        return frame, {"columns": []}

    scalers = {
        "standard": StandardScaler(),
        "minmax": MinMaxScaler(),
        "normalize": Normalizer(),
    }
    scaler = scalers[kind]

    # Nilai kosong harus diisi lebih dulu: scaler sklearn menolak NaN.
    subset = frame[columns].fillna(frame[columns].median())
    frame[columns] = scaler.fit_transform(subset)

    detail = {"columns": columns}

    if kind == "standard":
        detail["mean"] = {name: float(value) for name, value in zip(columns, scaler.mean_)}
        detail["scale"] = {name: float(value) for name, value in zip(columns, scaler.scale_)}
    elif kind == "minmax":
        detail["min"] = {name: float(value) for name, value in zip(columns, scaler.data_min_)}
        detail["max"] = {name: float(value) for name, value in zip(columns, scaler.data_max_)}

    return frame, detail


def _pca(frame: pd.DataFrame, step: dict) -> tuple:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    columns = _target_columns(frame, step, loader.numeric_columns(frame))

    if len(columns) < 2:
        raise EngineError("PCA butuh minimal dua kolom numerik.")

    components = int(step.get("components", min(len(columns), 3)))
    components = max(1, min(components, len(columns)))

    subset = frame[columns].fillna(frame[columns].median())
    scaled = StandardScaler().fit_transform(subset)
    pca = PCA(n_components=components, random_state=42)
    transformed = pca.fit_transform(scaled)

    keep_original = bool(step.get("keep_original", False))
    reduced = pd.DataFrame(
        transformed,
        columns=[f"PC{index + 1}" for index in range(components)],
        index=frame.index,
    )

    frame = pd.concat([frame if keep_original else frame.drop(columns=columns), reduced], axis=1)

    return frame, {
        "columns": columns,
        "components": components,
        "explained_variance": [float(value) for value in pca.explained_variance_ratio_],
        "total_explained": float(pca.explained_variance_ratio_.sum()),
        "loadings": [
            {
                "component": f"PC{index + 1}",
                "weights": {
                    name: round(float(weight), 4)
                    for name, weight in zip(columns, pca.components_[index])
                },
            }
            for index in range(components)
        ],
    }


STEPS = {
    "label_encoding": _label_encoding,
    "one_hot": _one_hot,
    "standard_scaling": lambda frame, step: _scale(frame, step, "standard"),
    "minmax_scaling": lambda frame, step: _scale(frame, step, "minmax"),
    "normalization": lambda frame, step: _scale(frame, step, "normalize"),
    "pca": _pca,
}


def transform(params: dict) -> dict:
    frame = loader.load(params)
    steps = params.get("steps") or []
    output_path = params.get("output_path")

    if not steps:
        raise EngineError("Belum ada langkah transformasi yang dipilih.")

    if not output_path:
        raise EngineError("Lokasi penyimpanan feature set tidak dikirim.")

    before_columns = list(frame.columns)
    applied = []

    # Kolom target dikecualikan dari transformasi apa pun: menskalakan atau
    # meng-encode target akan membuat model memprediksi besaran yang berbeda
    # dari yang dimaksud pengguna.
    target = params.get("target")
    protected = frame[[target]].copy() if target and target in frame.columns else None

    if protected is not None:
        frame = frame.drop(columns=[target])

    for step in steps:
        name = step.get("step")
        handler = STEPS.get(name)

        if handler is None:
            raise EngineError(
                f"Langkah '{name}' tidak dikenal. Pilihan: " + ", ".join(sorted(STEPS))
            )

        frame, detail = handler(frame, step)
        applied.append({"step": name, "detail": detail})

    if protected is not None:
        frame = pd.concat([frame, protected], axis=1)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8")

    return {
        "path": output_path,
        "row_count": int(len(frame)),
        "column_count": int(frame.shape[1]),
        "columns": [str(name) for name in frame.columns],
        "columns_before": before_columns,
        "steps": applied,
        "preview": {
            "columns": [str(name) for name in frame.columns[:12]],
            "rows": [
                [None if pd.isna(value) else str(value) for value in row]
                for row in frame.iloc[:8, :12].itertuples(index=False)
            ],
        },
    }


def selection(params: dict) -> dict:
    """Feature Selection: memeringkat kolom berdasarkan kekuatannya terhadap target.

    Memakai dua sudut pandang sekaligus — uji statistik univariat (cepat, tiap
    kolom sendiri-sendiri) dan kepentingan dari Random Forest (menangkap
    interaksi antar kolom) — karena keduanya sering tidak sepakat, dan
    perbedaannya sendiri informatif.
    """
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.feature_selection import f_classif, f_regression
    from sklearn.preprocessing import LabelEncoder

    frame = loader.load(params)
    (target,) = require(params, "target")

    if target not in frame.columns:
        raise EngineError(f'Kolom target "{target}" tidak ada pada dataset ini.')

    candidates = [
        name for name in frame.columns
        if name != target
        and not loader.is_identifier(frame[name])
        and loader.column_kind(frame[name]) != "datetime"
    ]

    if not candidates:
        raise EngineError("Tidak ada kolom yang bisa dinilai sebagai fitur.")

    subset = frame[candidates + [target]].dropna()

    if len(subset) < 20:
        raise EngineError("Baris lengkap terlalu sedikit untuk pemilihan fitur (minimal 20).")

    encoded = pd.DataFrame(index=subset.index)

    for name in candidates:
        column = subset[name]

        if loader.column_kind(column) in ("integer", "float"):
            encoded[name] = column
        else:
            encoded[name] = LabelEncoder().fit_transform(column.astype(str))

    is_classification = loader.column_kind(subset[target]) not in ("integer", "float")

    if is_classification:
        y = LabelEncoder().fit_transform(subset[target].astype(str))
        scores, p_values = f_classif(encoded, y)
        forest = RandomForestClassifier(n_estimators=120, random_state=42, n_jobs=-1)
    else:
        y = subset[target].to_numpy()
        scores, p_values = f_regression(encoded, y)
        forest = RandomForestRegressor(n_estimators=120, random_state=42, n_jobs=-1)

    forest.fit(encoded, y)
    importances = forest.feature_importances_

    features = [
        {
            "feature": name,
            "univariate_score": None if np.isnan(scores[index]) else float(scores[index]),
            "p_value": None if np.isnan(p_values[index]) else float(p_values[index]),
            "importance": float(importances[index]),
            "significant": bool(p_values[index] < 0.05) if not np.isnan(p_values[index]) else False,
            "type": loader.column_kind(subset[name]),
        }
        for index, name in enumerate(candidates)
    ]
    features.sort(key=lambda item: item["importance"], reverse=True)

    top_k = int(params.get("top_k", min(10, len(features))))
    recommended = [item["feature"] for item in features[:top_k]]

    return {
        "target": target,
        "task": "classification" if is_classification else "regression",
        "features": features,
        "recommended": recommended,
        "interpretation": (
            f'{len(recommended)} kolom teratas menyumbang '
            f'{sum(item["importance"] for item in features[:top_k]) * 100:.1f}% '
            "dari total kepentingan fitur."
        ),
    }
