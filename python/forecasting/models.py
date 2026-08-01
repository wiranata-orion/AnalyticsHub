"""Forecasting: ARIMA, SARIMA, Prophet, dan Holt-Winters.

Keempatnya dijalankan atas deret waktu yang sama dan dievaluasi dengan cara yang
sama — sebagian akhir data ditahan sebagai data uji, lalu model diminta
memprediksinya. Tanpa penahanan itu, "akurasi" hanya mengukur seberapa baik
model menghafal data yang sudah dilihatnya.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core import loader
from core.io import EngineError
from mining import timeseries

MIN_PERIODS = 12


def run(params: dict) -> dict:
    frame = loader.load(params)

    time_columns = loader.datetime_columns(frame)
    numeric = loader.numeric_columns(frame)

    if not time_columns:
        raise EngineError("Forecasting butuh kolom bertipe waktu; dataset ini tidak punya.")

    if not numeric:
        raise EngineError("Forecasting butuh kolom numerik untuk diproyeksikan.")

    time_column = params.get("time_column") or time_columns[0]
    value_column = params.get("value_column") or numeric[0]
    freq = params.get("freq") or timeseries.suggest_freq(
        pd.to_datetime(frame[time_column], errors="coerce").dropna()
    )

    series = timeseries.prepare(frame, time_column, value_column, freq)

    if len(series) < MIN_PERIODS:
        raise EngineError(
            f"Hanya terbentuk {len(series)} periode pada frekuensi '{freq}'. "
            f"Forecasting butuh minimal {MIN_PERIODS} periode."
        )

    horizon = int(params.get("horizon", 12))
    horizon = max(1, min(horizon, max(1, len(series) // 2)))

    # Data uji diambil dari ekor deret: peramalan selalu tentang masa depan,
    # jadi pembagiannya harus urut waktu, bukan acak.
    holdout = min(horizon, max(2, len(series) // 5))
    train = series.iloc[:-holdout]
    test = series.iloc[-holdout:]

    requested = params.get("models") or ["arima", "sarima", "holt_winters", "prophet"]
    period = timeseries._seasonal_period(freq) or 12

    runners = {
        "arima": lambda: _arima(train, test, horizon, seasonal=False, period=period),
        "sarima": lambda: _arima(train, test, horizon, seasonal=True, period=period),
        "holt_winters": lambda: _holt_winters(train, test, horizon, period),
        "prophet": lambda: _prophet(train, test, horizon, freq),
    }

    results = []

    for name in requested:
        runner = runners.get(name)

        if runner is None:
            continue

        try:
            outcome = runner()
            outcome.update({"model": name, "status": "ready"})
            results.append(outcome)
        except Exception as error:
            # Satu model yang gagal tidak menggagalkan yang lain — pengguna tetap
            # mendapat perbandingan dari model yang berhasil.
            results.append({
                "model": name,
                "status": "failed",
                "error": f"{type(error).__name__}: {str(error)[:200]}",
            })

    succeeded = [item for item in results if item["status"] == "ready"]

    if not succeeded:
        raise EngineError(
            "Tidak ada model peramalan yang berhasil dijalankan pada deret ini."
        )

    best = min(succeeded, key=lambda item: item["metrics"]["rmse"])

    future_index = pd.date_range(
        start=series.index[-1], periods=horizon + 1, freq=freq
    )[1:]

    return {
        "time_column": time_column,
        "value_column": value_column,
        "freq": freq,
        "periods": int(len(series)),
        "horizon": horizon,
        "holdout": int(holdout),
        "history": {
            "labels": [stamp.isoformat() for stamp in series.index],
            "values": [float(value) for value in series.to_numpy()],
        },
        "future_labels": [stamp.isoformat() for stamp in future_index],
        "results": [
            {key: value for key, value in item.items() if not key.startswith("_")}
            for item in results
        ],
        "best": best["model"],
        "interpretation": (
            f'{_label(best["model"])} paling akurat pada {holdout} periode uji '
            f'(RMSE {best["metrics"]["rmse"]:.2f}), dan memproyeksikan '
            f'{"kenaikan" if best["forecast"][-1] >= series.iloc[-1] else "penurunan"} '
            f"pada {horizon} periode ke depan."
        ),
    }


def _label(name: str) -> str:
    return {
        "arima": "ARIMA",
        "sarima": "SARIMA",
        "holt_winters": "Holt-Winters",
        "prophet": "Prophet",
    }.get(name, name)


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    errors = actual - predicted

    with np.errstate(divide="ignore", invalid="ignore"):
        mape = np.mean(np.abs(errors / np.where(actual == 0, np.nan, actual))) * 100

    return {
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "mae": float(np.mean(np.abs(errors))),
        "mape": None if np.isnan(mape) else float(mape),
    }


def _arima(train: pd.Series, test: pd.Series, horizon: int, seasonal: bool, period: int) -> dict:
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    order = (1, 1, 1)
    seasonal_order = (1, 1, 1, period) if seasonal and len(train) > period * 2 else (0, 0, 0, 0)

    if seasonal and seasonal_order == (0, 0, 0, 0):
        raise ValueError(
            f"Deret terlalu pendek untuk pola musiman {period} periode."
        )

    fitted = SARIMAX(
        train, order=order, seasonal_order=seasonal_order,
        enforce_stationarity=False, enforce_invertibility=False,
    ).fit(disp=False)

    validation = fitted.forecast(steps=len(test))

    # Model dilatih ulang pada seluruh data sebelum meramal masa depan: data uji
    # tetap berguna dan tidak dibuang begitu evaluasinya selesai.
    final = SARIMAX(
        pd.concat([train, test]), order=order, seasonal_order=seasonal_order,
        enforce_stationarity=False, enforce_invertibility=False,
    ).fit(disp=False)

    prediction = final.get_forecast(steps=horizon)
    interval = prediction.conf_int()

    return {
        "label": "SARIMA" if seasonal else "ARIMA",
        "order": list(order),
        "seasonal_order": list(seasonal_order),
        "metrics": _metrics(test.to_numpy(), np.asarray(validation)),
        "validation": [float(value) for value in np.asarray(validation)],
        "forecast": [float(value) for value in np.asarray(prediction.predicted_mean)],
        "lower": [float(value) for value in interval.iloc[:, 0].to_numpy()],
        "upper": [float(value) for value in interval.iloc[:, 1].to_numpy()],
        "aic": float(final.aic),
    }


def _holt_winters(train: pd.Series, test: pd.Series, horizon: int, period: int) -> dict:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    seasonal = "add" if len(train) > period * 2 else None

    fitted = ExponentialSmoothing(
        train, trend="add", seasonal=seasonal,
        seasonal_periods=period if seasonal else None,
    ).fit()

    validation = fitted.forecast(len(test))

    final = ExponentialSmoothing(
        pd.concat([train, test]), trend="add", seasonal=seasonal,
        seasonal_periods=period if seasonal else None,
    ).fit()

    forecast = final.forecast(horizon)

    return {
        "label": "Holt-Winters",
        "seasonal": bool(seasonal),
        "metrics": _metrics(test.to_numpy(), np.asarray(validation)),
        "validation": [float(value) for value in np.asarray(validation)],
        "forecast": [float(value) for value in np.asarray(forecast)],
        "lower": None,
        "upper": None,
    }


def _prophet(train: pd.Series, test: pd.Series, horizon: int, freq: str) -> dict:
    from prophet import Prophet

    def to_frame(series: pd.Series) -> pd.DataFrame:
        return pd.DataFrame({"ds": series.index, "y": series.to_numpy()})

    model = Prophet(
        yearly_seasonality="auto", weekly_seasonality="auto", daily_seasonality=False
    )
    model.fit(to_frame(train))

    validation_frame = model.predict(pd.DataFrame({"ds": test.index}))
    validation = validation_frame["yhat"].to_numpy()

    final = Prophet(
        yearly_seasonality="auto", weekly_seasonality="auto", daily_seasonality=False
    )
    final.fit(to_frame(pd.concat([train, test])))

    future = final.make_future_dataframe(periods=horizon, freq=freq)
    prediction = final.predict(future).tail(horizon)

    return {
        "label": "Prophet",
        "metrics": _metrics(test.to_numpy(), validation),
        "validation": [float(value) for value in validation],
        "forecast": [float(value) for value in prediction["yhat"].to_numpy()],
        "lower": [float(value) for value in prediction["yhat_lower"].to_numpy()],
        "upper": [float(value) for value in prediction["yhat_upper"].to_numpy()],
    }
