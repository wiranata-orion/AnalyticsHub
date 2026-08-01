"""Data Quality Assessment: enam dimensi dan satu skor keseluruhan.

    Completeness  seberapa banyak sel yang terisi
    Uniqueness    seberapa sedikit baris yang terduplikasi
    Validity      seberapa banyak nilai yang masuk akal untuk tipenya
    Consistency   seberapa seragam penulisan nilai pada kolom yang sama
    Accuracy      seberapa sedikit nilai yang menyimpang jauh dari pola
    Timeliness    seberapa baru data terakhir yang tercatat

Setiap dimensi bernilai 0-100 dan disertai temuan yang menjelaskan angkanya,
karena skor tanpa keterangan tidak memberi tahu apa yang harus diperbaiki.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from core import loader

# Bobot: kelengkapan dan keunikan paling menentukan layak-tidaknya data dipakai,
# sedangkan ketepatan waktu tidak relevan untuk sebagian dataset.
WEIGHTS = {
    "completeness": 0.25,
    "uniqueness": 0.20,
    "validity": 0.20,
    "consistency": 0.15,
    "accuracy": 0.15,
    "timeliness": 0.05,
}


def run(params: dict) -> dict:
    frame = loader.load(params)
    dimensions = [
        _completeness(frame),
        _uniqueness(frame),
        _validity(frame),
        _consistency(frame),
        _accuracy(frame),
        _timeliness(frame),
    ]

    scored = [item for item in dimensions if item["score"] is not None]
    total_weight = sum(WEIGHTS[item["key"]] for item in scored) or 1.0
    overall = sum(item["score"] * WEIGHTS[item["key"]] for item in scored) / total_weight

    return {
        "overall_score": round(float(overall), 2),
        "grade": _grade(overall),
        "dimensions": dimensions,
        "row_count": int(len(frame)),
        "column_count": int(frame.shape[1]),
        "interpretation": (
            f"Kualitas dataset {_grade(overall).lower()} dengan skor "
            f"{overall:.1f} dari 100. "
            + _weakest_words(scored)
        ),
    }


def _grade(score: float) -> str:
    if score >= 90:
        return "Sangat Baik"
    if score >= 75:
        return "Baik"
    if score >= 60:
        return "Cukup"
    if score >= 40:
        return "Kurang"

    return "Buruk"


def _weakest_words(scored: list) -> str:
    if not scored:
        return ""

    weakest = min(scored, key=lambda item: item["score"])

    if weakest["score"] >= 90:
        return "Tidak ada dimensi yang menonjol bermasalah."

    return f"Dimensi paling lemah: {weakest['label']} ({weakest['score']:.0f})."


def _completeness(frame: pd.DataFrame) -> dict:
    cells = frame.shape[0] * frame.shape[1]
    missing = int(frame.isna().sum().sum())
    score = (1 - missing / cells) * 100 if cells else 100.0

    worst = frame.isna().mean().sort_values(ascending=False)
    findings = [
        f'Kolom "{name}" kosong pada {value * 100:.1f}% baris.'
        for name, value in worst.head(3).items() if value > 0
    ]

    return {
        "key": "completeness",
        "label": "Completeness",
        "score": round(float(score), 2),
        "detail": f"{cells - missing} dari {cells} sel terisi.",
        "findings": findings or ["Seluruh sel terisi."],
    }


def _uniqueness(frame: pd.DataFrame) -> dict:
    comparable = [name for name in frame.columns if not loader.is_identifier(frame[name])]
    duplicates = int(frame.duplicated(subset=comparable or None).sum())
    score = (1 - duplicates / len(frame)) * 100 if len(frame) else 100.0

    return {
        "key": "uniqueness",
        "label": "Uniqueness",
        "score": round(float(score), 2),
        "detail": f"{duplicates} baris duplikat dari {len(frame)} baris.",
        "findings": (
            [f"{duplicates} baris berisi data yang sama persis dengan baris lain."]
            if duplicates else ["Tidak ada baris duplikat."]
        ),
    }


def _validity(frame: pd.DataFrame) -> dict:
    """Nilai yang tidak masuk akal untuk tipenya: teks pada kolom angka,
    tanggal di masa depan yang jauh, angka negatif pada kolom jumlah."""
    issues = 0
    checked = 0
    findings = []

    for name in frame.columns:
        series = frame[name].dropna()

        if series.empty:
            continue

        kind = loader.column_kind(series)
        checked += len(series)

        if kind in ("integer", "float"):
            # Kolom bernama jumlah/harga/stok tidak masuk akal bernilai negatif.
            if re.search(r"jumlah|harga|total|stok|umur|usia|qty|count|amount", name, re.I):
                invalid = int((series < 0).sum())

                if invalid:
                    issues += invalid
                    findings.append(f'Kolom "{name}" punya {invalid} nilai negatif.')
        elif kind == "datetime":
            future = int((series > pd.Timestamp.now() + pd.Timedelta(days=365 * 5)).sum())

            if future:
                issues += future
                findings.append(f'Kolom "{name}" punya {future} tanggal jauh di masa depan.')
        elif kind in ("category", "text"):
            blank = int(series.astype(str).str.strip().eq("").sum())

            if blank:
                issues += blank
                findings.append(f'Kolom "{name}" punya {blank} nilai berupa teks kosong.')

    score = (1 - issues / checked) * 100 if checked else 100.0

    return {
        "key": "validity",
        "label": "Validity",
        "score": round(float(max(0.0, score)), 2),
        "detail": f"{issues} nilai tidak masuk akal dari {checked} nilai terisi.",
        "findings": findings or ["Tidak ditemukan nilai yang menyalahi tipenya."],
    }


def _consistency(frame: pd.DataFrame) -> dict:
    """Keseragaman penulisan: "Jakarta", "jakarta", dan "JAKARTA " seharusnya
    satu nilai yang sama, bukan tiga kategori berbeda."""
    issues = 0
    checked = 0
    findings = []

    for name in loader.categorical_columns(frame, max_unique=1000):
        series = frame[name].dropna().astype(str)

        if series.empty:
            continue

        checked += 1
        normalized = series.str.strip().str.lower()
        collapsed = normalized.nunique()
        original = series.nunique()

        if collapsed < original:
            issues += 1
            findings.append(
                f'Kolom "{name}" punya {original - collapsed} nilai yang sebenarnya sama '
                "namun berbeda huruf besar/kecil atau spasi."
            )

    score = (1 - issues / checked) * 100 if checked else 100.0

    return {
        "key": "consistency",
        "label": "Consistency",
        "score": round(float(score), 2),
        "detail": f"{issues} dari {checked} kolom kategori punya penulisan tidak seragam.",
        "findings": findings or ["Penulisan nilai kategori sudah seragam."],
    }


def _accuracy(frame: pd.DataFrame) -> dict:
    """Didekati lewat proporsi nilai ekstrem: makin banyak nilai yang jauh dari
    pola umum, makin besar kemungkinan ada kesalahan pencatatan."""
    numeric = loader.numeric_columns(frame)

    if not numeric or frame.empty:
        return {
            "key": "accuracy",
            "label": "Accuracy",
            "score": None,
            "detail": "Tidak ada kolom numerik untuk dinilai.",
            "findings": ["Dimensi ini dilewati karena dataset tidak punya kolom numerik."],
        }

    total = 0
    findings = []

    for name in numeric:
        values = frame[name].dropna()

        if values.empty:
            continue

        q1, q3 = values.quantile(0.25), values.quantile(0.75)
        iqr = q3 - q1
        outliers = int(((values < q1 - 3 * iqr) | (values > q3 + 3 * iqr)).sum())
        total += outliers

        if outliers:
            findings.append(f'Kolom "{name}" punya {outliers} nilai sangat ekstrem.')

    cells = len(numeric) * len(frame)
    score = (1 - total / cells) * 100 if cells else 100.0

    return {
        "key": "accuracy",
        "label": "Accuracy",
        "score": round(float(score), 2),
        "detail": f"{total} nilai berada jauh di luar batas wajar (3× IQR).",
        "findings": findings or ["Tidak ada nilai yang menyimpang secara ekstrem."],
    }


def _timeliness(frame: pd.DataFrame) -> dict:
    columns = loader.datetime_columns(frame)

    if not columns:
        return {
            "key": "timeliness",
            "label": "Timeliness",
            "score": None,
            "detail": "Tidak ada kolom waktu untuk dinilai.",
            "findings": ["Dimensi ini dilewati karena dataset tidak punya kolom waktu."],
        }

    latest = max(frame[name].dropna().max() for name in columns if frame[name].notna().any())
    age_days = (pd.Timestamp.now() - latest).days

    # Data berumur setahun dianggap kehilangan seluruh nilai kebaruannya.
    score = max(0.0, min(100.0, (1 - age_days / 365) * 100))

    return {
        "key": "timeliness",
        "label": "Timeliness",
        "score": round(float(score), 2),
        "detail": f"Catatan terakhir berumur {age_days} hari ({latest.date()}).",
        "findings": [
            f"Data terbaru tercatat pada {latest.date()}."
            + (" Sudah cukup lama, pertimbangkan pembaruan." if age_days > 180 else "")
        ],
    }
