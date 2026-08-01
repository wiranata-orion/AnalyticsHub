"""Pemuatan dataset menjadi DataFrame.

Satu-satunya tempat berkas dibaca. Modul analisis tidak pernah membuka berkas
sendiri, sehingga aturan pembacaan (delimiter, encoding, deteksi tipe) berlaku
seragam dan hanya perlu diperbaiki di satu tempat.
"""

from __future__ import annotations

import os

import pandas as pd

from core.io import EngineError


def load(params: dict) -> pd.DataFrame:
    """Baca dataset sesuai parameter yang dikirim Laravel."""
    path = params.get("path")

    if not path:
        raise EngineError("Path dataset tidak dikirim.")

    if not os.path.isfile(path):
        raise EngineError(f"Berkas dataset tidak ditemukan: {path}")

    extension = os.path.splitext(path)[1].lower()
    has_header = params.get("has_header", True)

    try:
        if extension in (".xlsx", ".xls"):
            frame = pd.read_excel(path, header=0 if has_header else None)
        else:
            frame = pd.read_csv(
                path,
                sep=params.get("delimiter") or ",",
                encoding=params.get("encoding") or "utf-8",
                header=0 if has_header else None,
                low_memory=False,
            )
    except UnicodeDecodeError as error:
        raise EngineError(
            "Encoding berkas tidak cocok. Coba UTF-8, ISO-8859-1, atau "
            f"Windows-1252 pada opsi impor. ({error.reason})"
        ) from error
    except pd.errors.ParserError as error:
        raise EngineError(
            f"Struktur berkas tidak konsisten — periksa pemisah kolom. ({error})"
        ) from error

    if frame.empty:
        raise EngineError("Dataset tidak berisi satu baris pun.")

    if not has_header:
        frame.columns = [f"kolom_{index + 1}" for index in range(frame.shape[1])]

    frame.columns = [str(name).strip() for name in frame.columns]

    return _coerce_types(frame)


def _coerce_types(frame: pd.DataFrame) -> pd.DataFrame:
    """Kembalikan tipe yang terbaca sebagai teks ke bentuk aslinya.

    CSV tidak membawa informasi tipe, sehingga tanggal dan angka sering masuk
    sebagai object. Tanpa langkah ini kolom `tanggal` tidak akan pernah
    terdeteksi sebagai datetime dan seluruh fitur time series mati.
    """
    for column in frame.columns:
        series = frame[column]

        # Diperiksa lewat "bukan tipe yang sudah pasti" alih-alih "bertipe
        # object": pandas 3.0 membaca kolom teks sebagai dtype `str` tersendiri,
        # sehingga pemeriksaan is_object_dtype akan melewatkannya dan kolom
        # tanggal tidak pernah terkonversi.
        if (
            pd.api.types.is_numeric_dtype(series)
            or pd.api.types.is_datetime64_any_dtype(series)
            or pd.api.types.is_bool_dtype(series)
        ):
            continue

        if series.dropna().empty:
            continue

        converted = pd.to_datetime(series, errors="coerce", format="mixed")

        if converted.notna().mean() >= 0.9:
            frame[column] = converted
            continue

        numeric = pd.to_numeric(
            series.astype(str).str.replace(r"\s", "", regex=True),
            errors="coerce",
        )

        if numeric.notna().mean() >= 0.95:
            frame[column] = numeric

    return frame


def column_kind(series: pd.Series) -> str:
    """Tipe kolom dalam kosakata yang dipakai antarmuka."""
    if pd.api.types.is_bool_dtype(series):
        return "boolean"

    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    if pd.api.types.is_integer_dtype(series):
        return "integer"

    if pd.api.types.is_float_dtype(series):
        return "float"

    non_null = series.dropna()

    if non_null.empty:
        return "text"

    # Teks dengan nilai berulang adalah kategori; yang hampir seluruhnya unik
    # adalah teks bebas atau identitas baris.
    ratio = non_null.nunique() / len(non_null)

    return "text" if ratio > 0.6 and non_null.nunique() > 50 else "category"


def is_identifier(series: pd.Series) -> bool:
    """Kolom yang nilainya unik di setiap baris bukan variabel yang bisa dianalisis."""
    non_null = series.dropna()

    if len(non_null) < 2 or pd.api.types.is_float_dtype(series):
        return False

    return non_null.nunique() == len(non_null)


def numeric_columns(frame: pd.DataFrame, exclude_identifier: bool = True) -> list:
    columns = [
        name for name in frame.columns
        if column_kind(frame[name]) in ("integer", "float")
    ]

    if not exclude_identifier:
        return columns

    return [name for name in columns if not is_identifier(frame[name])]


def categorical_columns(frame: pd.DataFrame, max_unique: int = 50) -> list:
    return [
        name for name in frame.columns
        if column_kind(frame[name]) in ("category", "boolean")
        and frame[name].nunique(dropna=True) <= max_unique
        and not is_identifier(frame[name])
    ]


def datetime_columns(frame: pd.DataFrame) -> list:
    return [name for name in frame.columns if column_kind(frame[name]) == "datetime"]


def sample(frame: pd.DataFrame, limit: int, seed: int = 42) -> pd.DataFrame:
    """Sampel acak deterministik untuk analisis yang mahal.

    Pairplot, SHAP, dan AutoML tidak menjadi lebih benar dengan jutaan baris,
    tetapi menjadi jauh lebih lambat.
    """
    if len(frame) <= limit:
        return frame

    return frame.sample(n=limit, random_state=seed).sort_index()
