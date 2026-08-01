"""Inti pelatihan model terbimbing.

Dipakai bersama oleh Data Mining (classification/regression), Machine Learning
(latih satu model), dan AutoML (mencoba banyak algoritma sekaligus). Menaruhnya
di satu tempat memastikan angka evaluasi yang muncul di ketiga halaman itu
dihitung dengan cara yang persis sama — kalau tidak, model yang sama bisa
tampak punya akurasi berbeda tergantung halaman mana yang membukanya.
"""

from __future__ import annotations

import os
import time

import numpy as np
import pandas as pd

from core import loader
from core.io import EngineError

RANDOM_STATE = 42
MIN_ROWS = 20


def classifiers() -> dict:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import GaussianNB
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.svm import SVC
    from sklearn.tree import DecisionTreeClassifier
    from xgboost import XGBClassifier

    return {
        "random_forest": ("Random Forest", lambda: RandomForestClassifier(
            n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1)),
        "decision_tree": ("Decision Tree", lambda: DecisionTreeClassifier(
            random_state=RANDOM_STATE)),
        "xgboost": ("XGBoost", lambda: XGBClassifier(
            n_estimators=200, learning_rate=0.1, max_depth=5,
            random_state=RANDOM_STATE, verbosity=0, eval_metric="logloss")),
        "knn": ("K-Nearest Neighbors", lambda: KNeighborsClassifier(n_neighbors=5)),
        "naive_bayes": ("Naive Bayes", lambda: GaussianNB()),
        # probability=True dibutuhkan agar kurva ROC bisa dihitung.
        "svm": ("Support Vector Machine", lambda: SVC(
            probability=True, random_state=RANDOM_STATE)),
        "logistic_regression": ("Logistic Regression", lambda: LogisticRegression(
            max_iter=2000, random_state=RANDOM_STATE)),
    }


def regressors() -> dict:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.svm import SVR
    from sklearn.tree import DecisionTreeRegressor
    from xgboost import XGBRegressor

    return {
        "random_forest": ("Random Forest", lambda: RandomForestRegressor(
            n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1)),
        "decision_tree": ("Decision Tree", lambda: DecisionTreeRegressor(
            random_state=RANDOM_STATE)),
        "xgboost": ("XGBoost", lambda: XGBRegressor(
            n_estimators=200, learning_rate=0.1, max_depth=5,
            random_state=RANDOM_STATE, verbosity=0)),
        "gradient_boosting": ("Gradient Boosting", lambda: GradientBoostingRegressor(
            random_state=RANDOM_STATE)),
        "knn": ("K-Nearest Neighbors", lambda: KNeighborsRegressor(n_neighbors=5)),
        "svm": ("Support Vector Machine", lambda: SVR()),
        "linear_regression": ("Linear Regression", lambda: LinearRegression()),
        "ridge": ("Ridge Regression", lambda: Ridge(random_state=RANDOM_STATE)),
    }


def detect_task(series: pd.Series) -> str:
    return "regression" if loader.column_kind(series) in ("integer", "float") else "classification"


def prepare(frame: pd.DataFrame, target: str, features: list) -> dict:
    """Siapkan matriks fitur dan vektor target.

    Kolom kategori di-encode di sini, bukan diserahkan ke pengguna, supaya
    algoritma apa pun bisa langsung dipakai tanpa harus melewati Feature
    Engineering lebih dulu. Pemetaannya dikembalikan agar prediksi pada data baru
    memakai kode yang sama.
    """
    from sklearn.preprocessing import LabelEncoder

    if target not in frame.columns:
        raise EngineError(f'Kolom target "{target}" tidak ada pada dataset ini.')

    features = [name for name in features if name in frame.columns and name != target]

    if not features:
        raise EngineError("Pilih minimal satu kolom fitur yang ada pada dataset.")

    subset = frame[features + [target]].dropna()

    if len(subset) < MIN_ROWS:
        raise EngineError(
            f"Hanya {len(subset)} baris yang seluruh kolomnya terisi — "
            f"dibutuhkan minimal {MIN_ROWS} untuk melatih model."
        )

    encoders = {}
    matrix = pd.DataFrame(index=subset.index)

    for name in features:
        column = subset[name]

        if loader.column_kind(column) in ("integer", "float"):
            matrix[name] = column.astype(float)
        elif loader.column_kind(column) == "datetime":
            # Waktu diubah jadi angka agar tetap bisa dipakai sebagai fitur.
            matrix[name] = pd.to_datetime(column).astype("int64") // 10**9
        else:
            encoder = LabelEncoder()
            matrix[name] = encoder.fit_transform(column.astype(str))
            encoders[name] = {
                str(label): int(code) for code, label in enumerate(encoder.classes_)
            }

    task = detect_task(subset[target])

    if task == "classification":
        target_encoder = LabelEncoder()
        y = target_encoder.fit_transform(subset[target].astype(str))
        classes = [str(label) for label in target_encoder.classes_]

        if len(classes) < 2:
            raise EngineError(f'Kolom target "{target}" hanya berisi satu kelas.')
    else:
        y = subset[target].astype(float).to_numpy()
        classes = None

    return {
        "X": matrix,
        "y": y,
        "task": task,
        "features": features,
        "classes": classes,
        "encoders": encoders,
        "rows": int(len(subset)),
    }


def split(data: dict, test_size: float = 0.2):
    from sklearn.model_selection import train_test_split

    # Stratifikasi menjaga proporsi kelas di data uji; tanpa itu kelas minoritas
    # bisa hilang seluruhnya dan metriknya jadi menyesatkan.
    stratify = data["y"] if data["task"] == "classification" else None

    try:
        return train_test_split(
            data["X"], data["y"], test_size=test_size,
            random_state=RANDOM_STATE, stratify=stratify,
        )
    except ValueError:
        return train_test_split(
            data["X"], data["y"], test_size=test_size, random_state=RANDOM_STATE
        )


def evaluate(model, task: str, X_test, y_test, classes: list | None) -> dict:
    from sklearn import metrics

    started = time.perf_counter()
    predictions = model.predict(X_test)
    prediction_ms = int((time.perf_counter() - started) * 1000)

    if task == "regression":
        return {
            "metrics": {
                "r2": float(metrics.r2_score(y_test, predictions)),
                "rmse": float(np.sqrt(metrics.mean_squared_error(y_test, predictions))),
                "mae": float(metrics.mean_absolute_error(y_test, predictions)),
                "mape": float(
                    np.mean(np.abs((y_test - predictions) / np.where(y_test == 0, np.nan, y_test)))
                    * 100
                ) if np.any(y_test != 0) else None,
            },
            "prediction_time_ms": prediction_ms,
            "scatter": [
                {"x": float(actual), "y": float(predicted)}
                for actual, predicted in zip(y_test[:500], predictions[:500])
            ],
            "residuals": [float(actual - predicted) for actual, predicted in zip(y_test[:500], predictions[:500])],
        }

    labels = list(range(len(classes)))
    matrix = metrics.confusion_matrix(y_test, predictions, labels=labels)
    report = metrics.classification_report(
        y_test, predictions, labels=labels, target_names=classes,
        output_dict=True, zero_division=0,
    )

    roc = None

    # ROC hanya bermakna untuk dua kelas dan model yang bisa memberi peluang.
    if len(classes) == 2 and hasattr(model, "predict_proba"):
        try:
            probabilities = model.predict_proba(X_test)[:, 1]
            fpr, tpr, _ = metrics.roc_curve(y_test, probabilities)
            roc = {
                "points": [
                    {"x": round(float(x), 4), "y": round(float(y), 4)}
                    for x, y in zip(fpr, tpr)
                ],
                "auc": float(metrics.roc_auc_score(y_test, probabilities)),
                "positive_label": classes[1],
            }
        except Exception:
            roc = None

    return {
        "metrics": {
            "accuracy": float(metrics.accuracy_score(y_test, predictions)),
            "precision": float(report["macro avg"]["precision"]),
            "recall": float(report["macro avg"]["recall"]),
            "f1": float(report["macro avg"]["f1-score"]),
            "roc_auc": roc["auc"] if roc else None,
        },
        "prediction_time_ms": prediction_ms,
        "confusion_matrix": {"labels": classes, "matrix": matrix.tolist()},
        "per_class": [
            {
                "label": label,
                "precision": float(report[label]["precision"]),
                "recall": float(report[label]["recall"]),
                "f1": float(report[label]["f1-score"]),
                "support": int(report[label]["support"]),
            }
            for label in classes if label in report
        ],
        "roc": roc,
    }


def feature_importance(model, features: list, X_test, y_test) -> list:
    """Kepentingan fitur, dengan permutation sebagai jalan terakhir.

    Model berbasis pohon menyediakannya langsung; model linear lewat koefisien.
    Untuk sisanya (KNN, SVM) dipakai permutation importance yang bekerja pada
    model apa pun karena hanya mengukur penurunan skor saat satu kolom diacak.
    """
    from sklearn.inspection import permutation_importance

    values = None

    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float)
    elif hasattr(model, "coef_"):
        coefficients = np.asarray(model.coef_, dtype=float)
        values = np.abs(coefficients).mean(axis=0) if coefficients.ndim > 1 else np.abs(coefficients)

    if values is None:
        try:
            result = permutation_importance(
                model, X_test, y_test, n_repeats=5, random_state=RANDOM_STATE, n_jobs=-1
            )
            values = np.clip(result.importances_mean, 0, None)
        except Exception:
            return []

    total = float(values.sum()) or 1.0

    return sorted(
        [
            {"feature": name, "importance": float(value), "share": round(float(value) / total * 100, 2)}
            for name, value in zip(features, values)
        ],
        key=lambda item: item["importance"],
        reverse=True,
    )


def learning_curve(builder, task: str, X_train, y_train, X_test, y_test) -> dict | None:
    """Skor pada porsi data latih yang makin besar.

    Jarak yang melebar antara kurva latih dan uji menandakan model mulai
    menghafal, bukan belajar.
    """
    from sklearn import metrics

    fractions = [0.2, 0.4, 0.6, 0.8, 1.0]
    train_scores, test_scores = [], []
    scorer = metrics.accuracy_score if task == "classification" else metrics.r2_score

    for fraction in fractions:
        size = max(MIN_ROWS // 2, int(len(X_train) * fraction))
        subset_X = X_train[:size]
        subset_y = y_train[:size]

        if task == "classification" and len(np.unique(subset_y)) < 2:
            return None

        try:
            model = builder().fit(subset_X, subset_y)
        except Exception:
            return None

        train_scores.append(round(float(scorer(subset_y, model.predict(subset_X))), 4))
        test_scores.append(round(float(scorer(y_test, model.predict(X_test))), 4))

    return {
        "labels": [f"{int(fraction * 100)}%" for fraction in fractions],
        "train": train_scores,
        "test": test_scores,
    }


def train(frame: pd.DataFrame, params: dict) -> dict:
    """Latih satu algoritma dan kembalikan model beserta evaluasinya."""
    target = params.get("target")
    features = params.get("features") or []
    algorithm = params.get("algorithm")

    data = prepare(frame, target, features)
    task = data["task"]
    zoo = classifiers() if task == "classification" else regressors()

    if algorithm not in zoo:
        algorithm = "random_forest"

    label, builder = zoo[algorithm]
    X_train, X_test, y_train, y_test = split(data, float(params.get("test_size", 0.2)))

    started = time.perf_counter()
    model = builder().fit(X_train, y_train)
    training_ms = int((time.perf_counter() - started) * 1000)

    evaluation = evaluate(model, task, X_test, y_test, data["classes"])

    return {
        "model": model,
        "data": data,
        "algorithm": algorithm,
        "algorithm_label": label,
        "task": task,
        "training_time_ms": training_ms,
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "evaluation": evaluation,
        "feature_importance": feature_importance(model, data["features"], X_test, y_test),
        "learning_curve": learning_curve(builder, task, X_train, y_train, X_test, y_test),
        "splits": (X_train, X_test, y_train, y_test),
    }


def save_artifact(bundle: dict, path: str) -> str:
    """Simpan model agar bisa dipakai lagi tanpa melatih ulang."""
    import joblib

    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(
        {
            "model": bundle["model"],
            "features": bundle["data"]["features"],
            "encoders": bundle["data"]["encoders"],
            "classes": bundle["data"]["classes"],
            "task": bundle["task"],
            "target": bundle["data"].get("target"),
        },
        path,
    )

    return path


def load_artifact(path: str) -> dict:
    import joblib

    if not os.path.isfile(path):
        raise EngineError(
            "Berkas model tidak ditemukan. Model mungkin sudah dihapus — latih ulang."
        )

    return joblib.load(path)
