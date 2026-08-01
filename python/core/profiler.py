"""Profiling dataset: karakteristik setiap kolom.

Hasil modul ini adalah fondasi seluruh fitur lain. Rekomendasi algoritma,
pemilihan target di Machine Learning, penilaian kualitas data, dan pemilihan
grafik otomatis semuanya membaca profil yang sama, sehingga angka yang muncul di
satu halaman tidak pernah berbeda dengan halaman lain.
"""

from __future__ import annotations

import pandas as pd

from core import loader

# Batas Tukey. Ambang yang sama dipakai halaman Cleaning dan deteksi anomali
# supaya kata "outlier" berarti hal yang persis sama di seluruh aplikasi.
IQR_MULTIPLIER = 1.5

HISTOGRAM_BINS = 10
TOP_VALUES = 12


def profile_column(series: pd.Series, position: int) -> dict:
    kind = loader.column_kind(series)
    total = len(series)
    missing = int(series.isna().sum())
    non_null = series.dropna()

    profile = {
        "position": position,
        "name": str(series.name),
        "type": kind,
        "missing_count": missing,
        "missing_percent": round(missing / total * 100, 4) if total else 0.0,
        "unique_count": int(non_null.nunique()),
        "is_identifier": loader.is_identifier(series),
        "mean": None,
        "std": None,
        "min": None,
        "q1": None,
        "median": None,
        "q3": None,
        "max": None,
        "skewness": None,
        "kurtosis": None,
        "outlier_count": 0,
        "top_values": None,
        "histogram": None,
    }

    if kind in ("integer", "float") and not non_null.empty:
        profile.update(_numeric_profile(non_null))
    elif kind in ("category", "boolean", "text") and not non_null.empty:
        profile["top_values"] = _top_values(non_null)
    elif kind == "datetime" and not non_null.empty:
        profile["min"] = None
        profile["max"] = None
        profile["range"] = {
            "start": non_null.min().isoformat(),
            "end": non_null.max().isoformat(),
        }

    return profile


def _numeric_profile(values: pd.Series) -> dict:
    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - IQR_MULTIPLIER * iqr
    upper = q3 + IQR_MULTIPLIER * iqr
    outliers = values[(values < lower) | (values > upper)]

    counts, edges = _histogram(values)

    return {
        "mean": float(values.mean()),
        "std": float(values.std()) if len(values) > 1 else 0.0,
        "min": float(values.min()),
        "q1": q1,
        "median": float(values.median()),
        "q3": q3,
        "max": float(values.max()),
        # Skewness dan kurtosis butuh minimal 3-4 titik; di bawah itu pandas
        # mengembalikan NaN yang akan menjadi null saat dibersihkan.
        "skewness": float(values.skew()) if len(values) > 2 else None,
        "kurtosis": float(values.kurtosis()) if len(values) > 3 else None,
        "outlier_count": int(len(outliers)),
        "lower_fence": float(max(values.min(), lower)),
        "upper_fence": float(min(values.max(), upper)),
        "histogram": {"counts": counts, "edges": edges},
    }


def _histogram(values: pd.Series) -> tuple:
    counts, edges = pd.cut(values, bins=HISTOGRAM_BINS, retbins=True)
    frequency = counts.value_counts(sort=False).tolist()

    return [int(item) for item in frequency], [float(edge) for edge in edges]


def _top_values(values: pd.Series) -> list:
    total = len(values)
    counts = values.astype(str).value_counts().head(TOP_VALUES)

    return [
        {
            "value": str(index),
            "count": int(count),
            "share": round(count / total * 100, 4),
        }
        for index, count in counts.items()
    ]


def correlation_matrix(frame: pd.DataFrame, columns: list, method: str = "pearson") -> dict | None:
    """Matriks korelasi antar kolom numerik."""
    if len(columns) < 2:
        return None

    matrix = frame[columns].corr(method=method, numeric_only=True)

    return {
        "columns": [str(name) for name in matrix.columns],
        "matrix": [[round(float(value), 4) for value in row] for row in matrix.values],
        "method": method,
    }


def run(frame: pd.DataFrame) -> dict:
    """Profil lengkap satu dataset."""
    columns = [
        profile_column(frame[name], position)
        for position, name in enumerate(frame.columns)
    ]

    numeric = loader.numeric_columns(frame)
    categorical = loader.categorical_columns(frame)
    datetimes = loader.datetime_columns(frame)

    # Duplikat dihitung tanpa kolom identitas: dua baris dengan isi sama tetap
    # duplikat walaupun nomor transaksinya berbeda.
    comparable = [name for name in frame.columns if not loader.is_identifier(frame[name])]
    duplicate_rows = int(frame.duplicated(subset=comparable or None).sum())

    cells = frame.shape[0] * frame.shape[1]
    missing_cells = int(frame.isna().sum().sum())
    outlier_total = sum(column["outlier_count"] for column in columns)

    return {
        "row_count": int(frame.shape[0]),
        "column_count": int(frame.shape[1]),
        "columns": columns,
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "datetime_columns": datetimes,
        "identifier_columns": [
            name for name in frame.columns if loader.is_identifier(frame[name])
        ],
        "duplicate_rows": duplicate_rows,
        "missing_cells": missing_cells,
        "missing_percent": round(missing_cells / cells * 100, 4) if cells else 0.0,
        "outlier_ratio": round(
            outlier_total / (len(numeric) * frame.shape[0]), 6
        ) if numeric and frame.shape[0] else 0.0,
        "correlation": correlation_matrix(frame, numeric[:12]),
        "preview": _preview(frame),
        "problematic_preview": _problematic_preview(frame),
    }


def _preview(frame: pd.DataFrame, rows: int = 10) -> dict:
    if frame.empty:
        return {
            "columns": [],
            "types": [],
            "rows": [],
        }

    head = frame.head(rows)

    return {
        "columns": ["Baris", *[str(name) for name in head.columns]],
        "types": ["number", *[loader.column_kind(frame[name]) for name in head.columns]],
        "rows": [
            [
                int(index) + 1,
                *[None if pd.isna(value) else str(value) for value in row],
            ]
            for index, row in zip(head.index, head.itertuples(index=False))
        ],
    }


def _problematic_preview(frame: pd.DataFrame, rows: int = 10) -> dict:
    mask = pd.Series(False, index=frame.index)

    if not frame.empty:
        mask |= frame.isna().any(axis=1)

        comparable = [name for name in frame.columns if not loader.is_identifier(frame[name])]
        if comparable:
            mask |= frame.duplicated(subset=comparable or None, keep=False)

        numeric = loader.numeric_columns(frame)
        if numeric:
            outlier_mask = pd.Series(False, index=frame.index)

            for name in numeric:
                values = frame[name]
                q1, q3 = values.quantile(0.25), values.quantile(0.75)
                iqr = q3 - q1
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                outlier_mask |= (values < lower) | (values > upper)

            mask |= outlier_mask

    problematic = frame[mask]

    if problematic.empty:
        return _preview(problematic, rows)

    return _preview(problematic, rows)
