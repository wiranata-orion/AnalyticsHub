"""Data Cleaning: menangani missing value, duplikat, outlier, dan tipe data.

Pembersihan selalu dikerjakan pada salinan dan disimpan sebagai berkas baru.
Berkas asli tidak pernah ditimpa: pengguna harus bisa membandingkan hasil dan
mengulang dengan strategi berbeda tanpa mengunggah ulang.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from core import loader
from core.io import EngineError


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


def _problematic_mask(frame: pd.DataFrame) -> pd.Series:
    mask = pd.Series(False, index=frame.index)

    if frame.empty:
        return mask

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

    return mask


def _issue_summary(frame: pd.DataFrame) -> list[dict]:
    issues = []

    missing_count = int(frame.isna().sum().sum())
    if missing_count > 0:
        issues.append({
            "key": "missing",
            "icon": "warning",
            "tone": "serious",
            "title": "Missing Values",
            "count": missing_count,
            "unit": "sel",
            "description": "Nilai kosong masih tersisa setelah cleaning.",
        })

    comparable = [name for name in frame.columns if not loader.is_identifier(frame[name])]
    duplicate_count = int(frame.duplicated(subset=comparable or None, keep=False).sum())
    if duplicate_count > 0:
        issues.append({
            "key": "duplicate",
            "icon": "copy",
            "tone": "warning",
            "title": "Duplikat",
            "count": duplicate_count,
            "unit": "baris",
            "description": "Baris duplikat masih terdeteksi setelah cleaning.",
        })

    numeric = loader.numeric_columns(frame)
    outlier_count = 0
    if numeric:
        outlier_mask = pd.Series(False, index=frame.index)

        for name in numeric:
            values = frame[name]
            q1, q3 = values.quantile(0.25), values.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            outlier_mask |= (values < lower) | (values > upper)

        outlier_count = int(outlier_mask.sum())

    if outlier_count > 0:
        issues.append({
            "key": "outlier",
            "icon": "chart",
            "tone": "warning",
            "title": "Outliers",
            "count": outlier_count,
            "unit": "indikasi",
            "description": "Nilai ekstrem masih terdeteksi pada data hasil cleaning.",
        })

    text_count = 0
    for name in frame.columns:
        if loader.column_kind(frame[name]) not in ("category", "text"):
            continue

        series = frame[name].astype("string")
        normalized = series.fillna("").str.strip()

        if (normalized != series.fillna("")).any() or (normalized.str.lower() != normalized).any():
            text_count += 1

    if text_count > 0:
        issues.append({
            "key": "type",
            "icon": "document",
            "tone": "critical",
            "title": "Normalisasi Teks",
            "count": text_count,
            "unit": "kolom",
            "description": "Masih ada kolom teks yang perlu dinormalisasi.",
        })

    return issues


def _apply_strategies(frame: pd.DataFrame, strategies: dict) -> tuple[pd.DataFrame, dict]:
    frame, missing = _handle_missing(frame, strategies.get("missing", "median"))
    frame, duplicates = _handle_duplicates(frame, strategies.get("duplicate", "keep_first"))
    frame, outliers = _handle_outliers(frame, strategies.get("outlier", "keep"))
    frame, text = _handle_text(frame, strategies.get("text"))

    return frame, {
        "missing": missing,
        "duplicates": duplicates,
        "outliers": outliers,
        "text": text,
    }


def _resolve_columns(frame: pd.DataFrame, strategy) -> list[str]:
    if isinstance(strategy, dict):
        columns = strategy.get("columns") or strategy.get("subset")

        if isinstance(columns, list) and columns:
            return [name for name in columns if name in frame.columns]

    return list(frame.columns)


def _handle_missing(frame: pd.DataFrame, strategy) -> tuple[pd.DataFrame, dict]:
    before = int(frame.isna().sum().sum())

    if isinstance(strategy, dict):
        method = strategy.get("method") or strategy.get("strategy") or "median"
        columns = _resolve_columns(frame, strategy)
        custom_value = strategy.get("value")
        if custom_value is None:
            custom_value = strategy.get("custom_value")
        custom_values = strategy.get("custom_values")
        if not isinstance(custom_values, dict):
            custom_values = {}
    else:
        method = strategy
        columns = list(frame.columns)
        custom_value = None
        custom_values = {}

    if method == "drop_rows":
        frame = frame.dropna()
    elif method in ("mean", "median"):
        for name in columns:
            if not pd.api.types.is_numeric_dtype(frame[name]):
                continue

            filler = frame[name].mean() if method == "mean" else frame[name].median()
            frame[name] = frame[name].fillna(filler)
    elif method == "mode":
        for name in columns:
            mode = frame[name].mode(dropna=True)

            if not mode.empty:
                frame[name] = frame[name].fillna(mode.iloc[0])
    elif method == "custom_value":
        for name in columns:
            if name not in frame.columns:
                continue

            value = custom_values.get(name, custom_value)

            if value is None:
                value = "Unknown"

            frame[name] = frame[name].fillna(value)
    elif method == "forward_fill":
        frame[columns] = frame[columns].ffill()
    elif method == "backward_fill":
        frame[columns] = frame[columns].bfill()

    return frame, {
        "before": before,
        "after": int(frame.isna().sum().sum()),
    }


def _handle_duplicates(frame: pd.DataFrame, strategy) -> tuple[pd.DataFrame, dict]:
    if isinstance(strategy, dict):
        subset = strategy.get("subset") or strategy.get("columns")
        keep = strategy.get("keep") or "first"
        if isinstance(subset, list):
            subset = [name for name in subset if name in frame.columns]
            subset = subset or None
    else:
        subset = None
        keep = strategy

    comparable = [name for name in frame.columns if not loader.is_identifier(frame[name])]
    subset = subset or comparable or None
    before = int(frame.duplicated(subset=subset).sum())

    if keep == "drop_all":
        frame = frame.drop_duplicates(subset=subset, keep=False)
    elif keep == "keep_first":
        frame = frame.drop_duplicates(subset=subset, keep="first")
    elif keep == "keep_last":
        frame = frame.drop_duplicates(subset=subset, keep="last")

    return frame, {"removed": before - int(frame.duplicated(subset=subset).sum())}


def _handle_outliers(frame: pd.DataFrame, strategy) -> tuple[pd.DataFrame, dict]:
    if isinstance(strategy, dict):
        method = strategy.get("method") or "keep"
        columns = _resolve_columns(frame, strategy)
    else:
        method = strategy
        columns = loader.numeric_columns(frame)

    if method == "keep":
        return frame, {"affected": 0}

    affected = 0

    for name in columns:
        if name not in frame.columns or not pd.api.types.is_numeric_dtype(frame[name]):
            continue

        values = frame[name]
        q1, q3 = values.quantile(0.25), values.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr

        if method == "iqr_remove":
            mask = (values < lower) | (values > upper)
            affected += int(mask.sum())
            frame = frame[~mask]
        elif method == "zscore_remove":
            std = values.std()

            if std and std > 0:
                mask = ((values - values.mean()).abs() / std) > 3
                affected += int(mask.sum())
                frame = frame[~mask]
        elif method == "winsorize":
            # Nilai ekstrem dipangkas ke batas, bukan dibuang: barisnya tetap
            # dihitung pada analisis lain yang tidak memakai kolom ini.
            affected += int(((values < lower) | (values > upper)).sum())
            frame[name] = values.clip(lower, upper)

    return frame, {"affected": affected}


def _handle_text(frame: pd.DataFrame, strategy) -> tuple[pd.DataFrame, dict]:
    if not strategy:
        return frame, {"affected": 0}

    if isinstance(strategy, dict):
        columns = _resolve_columns(frame, strategy)
        method = strategy.get("method") or "trim"
    else:
        columns = [name for name in frame.columns if loader.column_kind(frame[name]) in ("category", "text")]
        method = strategy

    affected = 0

    for name in columns:
        if name not in frame.columns or loader.column_kind(frame[name]) not in ("category", "text"):
            continue

        series = frame[name].astype("string")

        if method == "trim":
            updated = series.str.strip()
        elif method == "lower":
            updated = series.str.lower()
        elif method == "upper":
            updated = series.str.upper()
        elif method == "title":
            updated = series.str.title()
        else:
            continue

        affected += int((series.fillna("") != updated.fillna("")).sum())
        frame[name] = updated

    return frame, {"affected": affected}


def run(params: dict) -> dict:
    frame = loader.load(params)
    original_rows = len(frame)
    strategies = params.get("strategies") or {}

    problematic = frame[_problematic_mask(frame)]
    preview_before = _preview(problematic)

    frame, stats = _apply_strategies(frame, strategies)
    missing = stats["missing"]
    duplicates = stats["duplicates"]
    outliers = stats["outliers"]
    text = stats["text"]

    preview_after_frame, _ = _apply_strategies(problematic.copy(), strategies)
    remaining_issues = _issue_summary(frame)

    if frame.empty:
        raise EngineError(
            "Seluruh baris terbuang oleh strategi yang dipilih. "
            "Pilih penanganan yang lebih longgar."
        )

    output_path = params.get("output_path")

    if not output_path:
        raise EngineError("Lokasi penyimpanan hasil pembersihan tidak dikirim.")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8")

    return {
        "path": output_path,
        "row_count": int(len(frame)),
        "column_count": int(frame.shape[1]),
        "rows_removed": int(original_rows - len(frame)),
        "missing": missing,
        "duplicates": duplicates,
        "outliers": outliers,
        "text": text,
        "issues": remaining_issues,
        "preview": {
            "before": preview_before,
            "after": _preview(preview_after_frame),
        },
        "impact": {
            "labels": ["Sebelum", "Sesudah"],
            "rows": [original_rows, int(len(frame))],
            "missing_cells": [missing["before"], missing["after"]],
            "series": [
                {"label": "Baris Valid", "data": [original_rows, int(len(frame))]},
                {"label": "Baris Bermasalah", "data": [int(problematic.shape[0]), 0]},
            ],
        },
    }
