"""Analisis deret waktu: tren, musiman, dan proyeksi sederhana.

Untuk peramalan lengkap (ARIMA, SARIMA, Prophet, Holt-Winters) lihat modul
`forecasting`. Modul ini menjawab pertanyaan yang lebih dulu muncul: apakah data
ini memang punya tren dan pola musiman?
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core import loader
from core.io import EngineError


def prepare(frame: pd.DataFrame, time_column: str, value_column: str, freq: str) -> pd.Series:
    """Ubah baris mentah menjadi deret waktu berfrekuensi tetap."""
    pair = frame[[time_column, value_column]].dropna()

    if pair.empty:
        raise EngineError("Tidak ada baris yang kolom waktu dan nilainya terisi.")

    pair[time_column] = pd.to_datetime(pair[time_column], errors="coerce")
    pair = pair.dropna().sort_values(time_column)

    series = pair.set_index(time_column)[value_column].astype(float)

    # Beberapa baris bisa jatuh pada periode yang sama; dirata-ratakan agar
    # indeksnya unik dan berjarak tetap — syarat semua model deret waktu.
    resampled = series.resample(freq).mean()

    # Periode kosong di tengah dijembatani secara linear; membiarkannya NaN
    # akan membuat statsmodels menolak data.
    return resampled.interpolate(method="linear").dropna()


def suggest_freq(index: pd.DatetimeIndex) -> str:
    """Frekuensi yang masuk akal dari rentang dan kerapatan data."""
    if len(index) < 2:
        return "D"

    span_days = (index.max() - index.min()).days or 1
    per_day = len(index) / span_days

    if per_day >= 12:
        return "h"
    if per_day >= 1:
        return "D"
    if span_days > 730:
        return "MS"

    return "W"


def run(params: dict) -> dict:
    from statsmodels.tsa.seasonal import seasonal_decompose
    from statsmodels.tsa.stattools import adfuller

    frame = loader.load(params)

    time_columns = loader.datetime_columns(frame)
    numeric = loader.numeric_columns(frame)

    if not time_columns:
        raise EngineError("Dataset ini tidak punya kolom waktu.")

    if not numeric:
        raise EngineError("Dataset ini tidak punya kolom numerik untuk dianalisis.")

    time_column = params.get("time_column") or time_columns[0]
    value_column = params.get("value_column") or numeric[0]
    freq = params.get("freq") or suggest_freq(
        pd.to_datetime(frame[time_column], errors="coerce").dropna()
    )

    series = prepare(frame, time_column, value_column, freq)

    if len(series) < 6:
        raise EngineError(
            f"Hanya terbentuk {len(series)} periode pada frekuensi '{freq}'. "
            "Pilih frekuensi yang lebih rapat."
        )

    labels = [stamp.isoformat() for stamp in series.index]
    values = [float(value) for value in series.to_numpy()]

    # Garis tren kuadrat terkecil atas indeks periode.
    positions = np.arange(len(series))
    slope, intercept = np.polyfit(positions, series.to_numpy(), 1)
    trend_line = [float(intercept + slope * position) for position in positions]

    window = max(3, len(series) // 8)
    moving = series.rolling(window=window, min_periods=1).mean()

    # Uji Augmented Dickey-Fuller: deret yang tidak stasioner perlu differencing
    # sebelum dimodelkan ARIMA — hasilnya dipakai halaman Forecasting.
    stationary = None

    if len(series) >= 12:
        adf_stat, adf_p = adfuller(series.to_numpy())[:2]
        stationary = {
            "statistic": float(adf_stat),
            "p_value": float(adf_p),
            "is_stationary": bool(adf_p < 0.05),
        }

    decomposition = None
    period = _seasonal_period(freq)

    if period and len(series) >= period * 2:
        parts = seasonal_decompose(series, model="additive", period=period)
        decomposition = {
            "period": period,
            "trend": [None if pd.isna(value) else float(value) for value in parts.trend],
            "seasonal": [None if pd.isna(value) else float(value) for value in parts.seasonal],
            "residual": [None if pd.isna(value) else float(value) for value in parts.resid],
        }

    direction = "naik" if slope > 0 else "turun" if slope < 0 else "datar"
    change = (values[-1] - values[0]) / values[0] * 100 if values[0] else 0.0

    return {
        "time_column": time_column,
        "value_column": value_column,
        "freq": freq,
        "periods": int(len(series)),
        "labels": labels,
        "values": values,
        "trend_line": trend_line,
        "moving_average": [float(value) for value in moving.to_numpy()],
        "moving_window": window,
        "slope": float(slope),
        "direction": direction,
        "change_percent": round(float(change), 2),
        "stationarity": stationary,
        "decomposition": decomposition,
        "interpretation": (
            f'"{value_column}" bergerak {direction} sepanjang {len(series)} periode, '
            f"berubah {change:+.1f}% dari awal ke akhir."
        ),
    }


def _seasonal_period(freq: str) -> int | None:
    return {"h": 24, "D": 7, "W": 52, "MS": 12, "M": 12, "QS": 4}.get(freq)
