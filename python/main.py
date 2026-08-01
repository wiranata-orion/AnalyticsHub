"""Titik masuk tunggal engine analisis AnalyticsHub.

Dipanggil Laravel lewat `App\\Services\\PythonEngine`:

    stdin  : {"command": "eda.univariate", "params": {"path": "...", ...}}
    stdout : {"ok": true, "data": {...}}   atau   {"ok": false, "error": "..."}

Semua analisis melewati berkas ini, sehingga pemuatan dataset, penanganan galat,
dan pembersihan nilai untuk JSON hanya ditulis sekali. Modul analisis cukup
mengembalikan dict biasa; sisanya diurus di sini.

Menambah perintah baru: tambahkan satu entri di HANDLERS.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import warnings

# Peringatan konvergensi sklearn/statsmodels muncul di stderr dan akan tercatat
# di log Laravel sebagai kebisingan tanpa mengubah keabsahan hasil.
warnings.filterwarnings("ignore")
os.environ.setdefault("PYTHONWARNINGS", "ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.io import EngineError, fail, ok  # noqa: E402


def _handlers() -> dict:
    """Peta perintah -> fungsi.

    Impor dilakukan di dalam fungsi supaya satu panggilan hanya memuat modul yang
    dipakainya. Tanpa ini, setiap perintah sekecil apa pun ikut menarik xgboost,
    shap, dan prophet — yang menambah beberapa detik pada setiap permintaan.
    """
    from core import cleaner, recommender
    from eda import analysis as eda
    from forecasting import models as forecasting
    from insight import generator as insight
    from ml import automl, predict, xai
    from mining import (
        anomaly,
        association,
        classification,
        clustering,
        regression,
        timeseries,
    )
    from preprocessing import engineering
    from quality import assessment
    from stats import descriptive, inferential

    return {
        # Dataset & profiling
        "dataset.profile": _profile,
        "dataset.preview": _preview,
        "dataset.clean": cleaner.run,
        # Rekomendasi & insight
        "recommendation.suggest": recommender.run,
        "insight.generate": insight.run,
        # Exploratory Data Analysis
        "eda.univariate": eda.univariate,
        "eda.bivariate": eda.bivariate,
        "eda.multivariate": eda.multivariate,
        "eda.correlation": eda.correlation,
        "eda.distribution": eda.distribution,
        "eda.pairplot": eda.pairplot,
        "eda.missing_pattern": eda.missing_pattern,
        "eda.feature_relationship": eda.feature_relationship,
        # Statistik
        "stats.descriptive": descriptive.run,
        "stats.inferential": inferential.run,
        # Feature engineering
        "feature.transform": engineering.transform,
        "feature.selection": engineering.selection,
        # Data mining
        "mining.clustering": clustering.run,
        "mining.classification": classification.run,
        "mining.regression": regression.run,
        "mining.association": association.run,
        "mining.anomaly": anomaly.run,
        "mining.timeseries": timeseries.run,
        # Machine learning
        "ml.train": automl.train_single,
        "ml.automl": automl.run,
        "ml.predict": predict.run,
        "ml.xai": xai.run,
        # Forecasting
        "forecast.run": forecasting.run,
        # Kualitas data
        "quality.assess": assessment.run,
    }


def _profile(params: dict) -> dict:
    from core import loader, profiler

    return profiler.run(loader.load(params))


def _preview(params: dict) -> dict:
    from core import loader, profiler

    frame = loader.load(params)
    limit = int(params.get("limit", 25))

    return profiler._preview(frame, rows=limit)


def main() -> int:
    try:
        raw = sys.stdin.read()
    except Exception as error:  # pragma: no cover - stdin selalu tersedia dari PHP
        print(json.dumps(fail(f"Gagal membaca masukan: {error}")))
        return 0

    if not raw.strip():
        print(json.dumps(fail("Tidak ada perintah yang dikirim ke engine.")))
        return 0

    try:
        request = json.loads(raw)
    except json.JSONDecodeError as error:
        print(json.dumps(fail(f"Masukan bukan JSON yang sah: {error}")))
        return 0

    command = request.get("command")
    params = request.get("params") or {}

    try:
        handlers = _handlers()
    except ImportError as error:
        print(json.dumps(fail(
            f"Modul engine belum lengkap: {error}. "
            "Jalankan pip install -r python/requirements.txt."
        )))
        return 0

    handler = handlers.get(command)

    if handler is None:
        tersedia = ", ".join(sorted(handlers))
        print(json.dumps(fail(
            f"Perintah '{command}' tidak dikenal. Yang tersedia: {tersedia}"
        )))
        return 0

    try:
        result = handler(params)
    except EngineError as error:
        # Kesalahan yang memang ditujukan untuk pengguna: tampilkan apa adanya.
        print(json.dumps(fail(str(error))))
        return 0
    except MemoryError:
        print(json.dumps(fail(
            "Dataset terlalu besar untuk dianalisis di memori. "
            "Coba pada sebagian data atau kurangi jumlah kolom."
        )))
        return 0
    except Exception as error:
        # Traceback lengkap ke stderr (masuk log Laravel), ringkasnya ke pengguna.
        traceback.print_exc(file=sys.stderr)
        print(json.dumps(fail(f"{type(error).__name__}: {error}")))
        return 0

    print(json.dumps(ok(result), ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
