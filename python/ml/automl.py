"""AutoML: mencoba beberapa algoritma lalu memilih yang terbaik.

Perbandingannya adil karena semua algoritma menerima pembagian latih/uji yang
persis sama (`random_state` tetap). Tanpa itu, selisih akurasi antar model bisa
sekadar berasal dari keberuntungan pembagian data, bukan dari kualitas modelnya.

Waktu latih dan waktu prediksi ikut dicatat karena model terbaik tidak selalu
yang skornya tertinggi — model yang sedikit kurang akurat tetapi jauh lebih
cepat sering lebih berguna di produksi.
"""

from __future__ import annotations

import time

from core import loader
from core.io import EngineError
from ml import supervised


def train_single(params: dict) -> dict:
    """Latih satu algoritma; dipakai halaman Machine Learning."""
    frame = loader.load(params)
    bundle = supervised.train(frame, params)

    artifact_path = params.get("artifact_path")
    saved = None

    if artifact_path:
        bundle["data"]["target"] = params.get("target")
        saved = supervised.save_artifact(bundle, artifact_path)

    return _serialize(bundle, artifact_path=saved)


def _serialize(bundle: dict, artifact_path: str | None = None) -> dict:
    evaluation = bundle["evaluation"]

    return {
        "task": bundle["task"],
        "algorithm": bundle["algorithm"],
        "algorithm_label": bundle["algorithm_label"],
        "target": bundle["data"].get("target"),
        "features": bundle["data"]["features"],
        "classes": bundle["data"]["classes"],
        "rows_used": bundle["data"]["rows"],
        "train_size": bundle["train_size"],
        "test_size": bundle["test_size"],
        "training_time_ms": bundle["training_time_ms"],
        "prediction_time_ms": evaluation["prediction_time_ms"],
        "metrics": evaluation["metrics"],
        "confusion_matrix": evaluation.get("confusion_matrix"),
        "per_class": evaluation.get("per_class"),
        "roc": evaluation.get("roc"),
        "scatter": evaluation.get("scatter"),
        "feature_importance": bundle["feature_importance"],
        "learning_curve": bundle["learning_curve"],
        "artifact_path": artifact_path,
    }


def run(params: dict) -> dict:
    """Coba banyak algoritma, bandingkan, dan tandai pemenangnya."""
    frame = loader.load(params)
    target = params.get("target")
    features = params.get("features") or []

    data = supervised.prepare(frame, target, features)
    task = data["task"]
    zoo = supervised.classifiers() if task == "classification" else supervised.regressors()

    requested = params.get("algorithms") or list(zoo.keys())
    algorithms = [name for name in requested if name in zoo]

    if not algorithms:
        raise EngineError(
            "Tidak ada algoritma yang dikenali. Pilihan: " + ", ".join(sorted(zoo))
        )

    X_train, X_test, y_train, y_test = supervised.split(
        data, float(params.get("test_size", 0.2))
    )

    key = "accuracy" if task == "classification" else "r2"
    results = []

    for name in algorithms:
        label, builder = zoo[name]

        try:
            started = time.perf_counter()
            model = builder().fit(X_train, y_train)
            training_ms = int((time.perf_counter() - started) * 1000)

            evaluation = supervised.evaluate(model, task, X_test, y_test, data["classes"])

            results.append({
                "algorithm": name,
                "label": label,
                "status": "ready",
                "metrics": evaluation["metrics"],
                "score": evaluation["metrics"].get(key),
                "training_time_ms": training_ms,
                "prediction_time_ms": evaluation["prediction_time_ms"],
                "confusion_matrix": evaluation.get("confusion_matrix"),
                "roc": evaluation.get("roc"),
                "_model": model,
                "_builder": builder,
            })
        except Exception as error:
            # Satu algoritma yang gagal tidak boleh menggagalkan seluruh
            # perbandingan; kegagalannya dilaporkan apa adanya di tabel.
            results.append({
                "algorithm": name,
                "label": label,
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
                "score": None,
            })

    succeeded = [item for item in results if item["status"] == "ready"]

    if not succeeded:
        raise EngineError("Tidak ada satu pun algoritma yang berhasil dilatih pada dataset ini.")

    best = max(succeeded, key=lambda item: item["score"] if item["score"] is not None else -1e9)

    artifact_path = params.get("artifact_path")
    saved = None

    if artifact_path:
        data["target"] = target
        saved = supervised.save_artifact(
            {"model": best["_model"], "data": data, "task": task}, artifact_path
        )

    importance = supervised.feature_importance(
        best["_model"], data["features"], X_test, y_test
    )
    curve = supervised.learning_curve(
        best["_builder"], task, X_train, y_train, X_test, y_test
    )

    for item in results:
        item.pop("_model", None)
        item.pop("_builder", None)

    results.sort(key=lambda item: (item["score"] is None, -(item["score"] or 0)))

    return {
        "task": task,
        "target": target,
        "features": data["features"],
        "classes": data["classes"],
        "rows_used": data["rows"],
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "metric_key": key,
        "results": results,
        "best": {
            "algorithm": best["algorithm"],
            "label": best["label"],
            "score": best["score"],
            "metrics": best["metrics"],
            "training_time_ms": best["training_time_ms"],
            "prediction_time_ms": best["prediction_time_ms"],
            "confusion_matrix": best.get("confusion_matrix"),
            "roc": best.get("roc"),
            "feature_importance": importance,
            "learning_curve": curve,
            "artifact_path": saved,
        },
        "interpretation": (
            f'{best["label"]} menjadi model terbaik dengan '
            f'{"akurasi" if task == "classification" else "R²"} '
            f'{best["score"]:.3f}, dilatih dalam {best["training_time_ms"]} ms '
            f"dari {len(succeeded)} algoritma yang berhasil dicoba."
        ),
    }
