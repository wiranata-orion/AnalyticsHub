"""Statistik deskriptif per kolom numerik.

Menyajikan seluruh ukuran yang diminta halaman Statistical Analysis: pemusatan
(mean, median, modus), penyebaran (varians, simpangan baku, rentang, IQR),
posisi (kuartil, persentil), dan bentuk (skewness, kurtosis).

Setiap ukuran disertai penjelasan singkat, karena angka seperti kurtosis 4,2
tidak berarti apa pun bagi sebagian besar pengguna tanpa keterangan.
"""

from __future__ import annotations

import pandas as pd

from core import loader
from core.io import EngineError

PERCENTILES = [1, 5, 10, 25, 50, 75, 90, 95, 99]


def run(params: dict) -> dict:
    frame = loader.load(params)
    columns = params.get("columns") or loader.numeric_columns(frame)

    if not columns:
        raise EngineError("Tidak ada kolom numerik untuk dihitung statistiknya.")

    results = [_describe(frame[name]) for name in columns if name in frame.columns]

    return {
        "row_count": int(len(frame)),
        "columns": [item for item in results if item is not None],
        "categorical": _categorical_summary(frame),
    }


def _describe(series: pd.Series) -> dict | None:
    values = series.dropna()

    if values.empty or not pd.api.types.is_numeric_dtype(values):
        return None

    mode = values.mode()
    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    mean = float(values.mean())
    std = float(values.std()) if len(values) > 1 else 0.0
    skew = float(values.skew()) if len(values) > 2 else None
    kurtosis = float(values.kurtosis()) if len(values) > 3 else None

    return {
        "column": str(series.name),
        "count": int(len(values)),
        "missing": int(series.isna().sum()),
        "mean": mean,
        "median": float(values.median()),
        # Modus bisa lebih dari satu; diambil yang pertama dan jumlahnya dicatat
        # supaya pengguna tahu nilainya tidak tunggal.
        "mode": float(mode.iloc[0]) if not mode.empty else None,
        "mode_count": int(len(mode)),
        "variance": float(values.var()) if len(values) > 1 else 0.0,
        "std": std,
        "min": float(values.min()),
        "max": float(values.max()),
        "range": float(values.max() - values.min()),
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        # Koefisien variasi menyamakan satuan, sehingga penyebaran dua kolom
        # dengan skala berbeda bisa dibandingkan.
        "cv": round(std / mean * 100, 2) if mean else None,
        "sem": float(values.sem()) if len(values) > 1 else 0.0,
        "skewness": skew,
        "kurtosis": kurtosis,
        "percentiles": {
            str(percentile): float(values.quantile(percentile / 100))
            for percentile in PERCENTILES
        },
        "interpretation": _words(mean, float(values.median()), skew, kurtosis),
    }


def _words(mean: float, median: float, skew: float | None, kurtosis: float | None) -> str:
    parts = []

    if skew is not None:
        if abs(skew) < 0.5:
            parts.append("sebarannya cukup simetris")
        elif skew > 0:
            parts.append(
                "sebarannya miring ke kanan — beberapa nilai besar menarik rata-rata ke atas"
            )
        else:
            parts.append(
                "sebarannya miring ke kiri — beberapa nilai kecil menarik rata-rata ke bawah"
            )

    if kurtosis is not None:
        if kurtosis > 3:
            parts.append("berekor tebal, nilai ekstrem lebih sering muncul daripada sebaran normal")
        elif kurtosis < -1:
            parts.append("berekor tipis, nilainya jarang jauh dari pusat")

    if mean and abs(mean - median) / abs(mean) > 0.1:
        parts.append("rata-rata dan median berbeda cukup jauh, median lebih mewakili data")

    return "Data ini " + ", ".join(parts) + "." if parts else "Sebaran data tergolong biasa."


def _categorical_summary(frame: pd.DataFrame) -> list:
    """Ringkasan kolom kategorikal: modus, kardinalitas, dan konsentrasinya."""
    summary = []

    for name in loader.categorical_columns(frame):
        values = frame[name].dropna().astype(str)

        if values.empty:
            continue

        counts = values.value_counts()
        top = counts.index[0]
        share = float(counts.iloc[0]) / len(values) * 100

        summary.append({
            "column": name,
            "count": int(len(values)),
            "missing": int(frame[name].isna().sum()),
            "unique": int(values.nunique()),
            "mode": str(top),
            "mode_share": round(share, 2),
            "interpretation": (
                f'Didominasi "{top}" ({share:.1f}% baris).'
                if share >= 50
                else f"Tersebar pada {values.nunique()} nilai berbeda."
            ),
        })

    return summary
