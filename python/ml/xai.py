"""Explainable AI: menjelaskan alasan model menghasilkan prediksinya.

Empat sudut pandang yang saling melengkapi:

    feature_importance  kolom mana yang paling berpengaruh secara keseluruhan
    shap                sumbangan tiap kolom, dan ke arah mana
    lime                penjelasan untuk satu baris tertentu
    decision_path       aturan yang dilalui satu baris (khusus model pohon)

SHAP dan LIME berjalan pada sampel, bukan seluruh dataset: keduanya menghitung
ulang prediksi ratusan kali per baris, sehingga menjalankannya pada data penuh
bisa memakan waktu berjam-jam tanpa mengubah kesimpulannya.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core import loader
from core.io import EngineError
from ml import supervised

SHAP_SAMPLE = 200
LIME_FEATURES = 10


def run(params: dict) -> dict:
    artifact_path = params.get("artifact_path")

    if not artifact_path:
        raise EngineError("Model belum disimpan sehingga belum bisa dijelaskan.")

    bundle = supervised.load_artifact(artifact_path)
    frame = loader.load(params)

    features = bundle["features"]
    target = bundle.get("target")
    missing = [name for name in features if name not in frame.columns]

    if missing:
        raise EngineError(
            "Dataset tidak memiliki kolom " + ", ".join(missing) + " yang dipakai model."
        )

    matrix, subset = _encode(frame, features, bundle)

    if matrix.empty:
        raise EngineError("Tidak ada baris lengkap untuk dijelaskan.")

    model = bundle["model"]
    task = bundle.get("task", "classification")
    classes = bundle.get("classes")

    methods = params.get("methods") or ["feature_importance", "shap", "lime", "decision_path"]
    output = {
        "task": task,
        "target": target,
        "features": features,
        "classes": classes,
        "rows_explained": int(len(matrix)),
        "available": [],
        "unavailable": [],
    }

    if "feature_importance" in methods:
        importance = supervised.feature_importance(model, features, matrix, None)

        if importance:
            output["feature_importance"] = importance
            output["available"].append("feature_importance")
        else:
            output["unavailable"].append({
                "method": "feature_importance",
                "reason": "Model ini tidak menyediakan kepentingan fitur.",
            })

    if "shap" in methods:
        output.update(_shap(model, matrix, features, task, output))

    if "lime" in methods:
        row_index = int(params.get("row", 0))
        output.update(_lime(model, matrix, features, task, classes, row_index, output))

    if "decision_path" in methods:
        output.update(_decision_path(model, matrix, features, classes, output))

    return output


def _encode(frame: pd.DataFrame, features: list, bundle: dict):
    encoders = bundle.get("encoders") or {}
    subset = frame[features].dropna()
    subset = loader.sample(subset, SHAP_SAMPLE)
    matrix = pd.DataFrame(index=subset.index)

    for name in features:
        column = subset[name]

        if name in encoders:
            matrix[name] = column.astype(str).map(encoders[name]).fillna(-1).astype(int)
        elif loader.column_kind(column) == "datetime":
            matrix[name] = pd.to_datetime(column).astype("int64") // 10**9
        else:
            matrix[name] = pd.to_numeric(column, errors="coerce").fillna(0).astype(float)

    return matrix, subset


def _shap(model, matrix: pd.DataFrame, features: list, task: str, output: dict) -> dict:
    try:
        import shap

        # Explainer generik menangani model apa pun; untuk model pohon SHAP
        # otomatis memakai jalur cepat TreeExplainer di baliknya.
        explainer = shap.Explainer(model, matrix)
        values = explainer(matrix, check_additivity=False)
        array = np.asarray(values.values)

        # Klasifikasi multi-kelas menghasilkan dimensi ketiga (per kelas);
        # dirata-ratakan agar bisa dibaca sebagai satu ukuran per fitur.
        if array.ndim == 3:
            array = np.abs(array).mean(axis=2)

        mean_abs = np.abs(array).mean(axis=0)
        total = float(mean_abs.sum()) or 1.0

        contributions = sorted(
            [
                {
                    "feature": name,
                    "mean_abs": float(mean_abs[index]),
                    "share": round(float(mean_abs[index]) / total * 100, 2),
                    # Arah rata-rata: positif berarti menaikkan prediksi.
                    "direction": "menaikkan" if float(array[:, index].mean()) >= 0 else "menurunkan",
                }
                for index, name in enumerate(features)
            ],
            key=lambda item: item["mean_abs"],
            reverse=True,
        )

        output["available"].append("shap")

        return {
            "shap": {
                "contributions": contributions,
                "sampled_rows": int(len(matrix)),
                "interpretation": (
                    f'Kolom "{contributions[0]["feature"]}" paling menentukan prediksi '
                    f'({contributions[0]["share"]:.1f}% dari total pengaruh), dan rata-rata '
                    f'{contributions[0]["direction"]} hasilnya.'
                    if contributions else ""
                ),
            }
        }
    except Exception as error:
        output["unavailable"].append({
            "method": "shap",
            "reason": f"SHAP tidak dapat dihitung untuk model ini ({type(error).__name__}).",
        })

        return {}


def _lime(model, matrix: pd.DataFrame, features: list, task: str,
          classes: list | None, row_index: int, output: dict) -> dict:
    try:
        from lime.lime_tabular import LimeTabularExplainer

        row_index = max(0, min(row_index, len(matrix) - 1))
        explainer = LimeTabularExplainer(
            matrix.to_numpy(),
            feature_names=features,
            class_names=classes,
            mode="classification" if task == "classification" else "regression",
            random_state=42,
        )

        predict_fn = model.predict_proba if task == "classification" and hasattr(
            model, "predict_proba"
        ) else model.predict

        explanation = explainer.explain_instance(
            matrix.iloc[row_index].to_numpy(),
            predict_fn,
            num_features=min(LIME_FEATURES, len(features)),
        )

        output["available"].append("lime")

        return {
            "lime": {
                "row": row_index,
                "values": {name: float(matrix.iloc[row_index][name]) for name in features[:8]},
                "explanations": [
                    {
                        "rule": str(rule),
                        "weight": float(weight),
                        "effect": "mendukung" if weight >= 0 else "menentang",
                    }
                    for rule, weight in explanation.as_list()
                ],
                "interpretation": (
                    "Setiap aturan menunjukkan seberapa besar kondisi tersebut mendorong "
                    "prediksi baris ini ke arah tertentu."
                ),
            }
        }
    except Exception as error:
        output["unavailable"].append({
            "method": "lime",
            "reason": f"LIME tidak dapat dijalankan ({type(error).__name__}).",
        })

        return {}


def _decision_path(model, matrix: pd.DataFrame, features: list,
                   classes: list | None, output: dict) -> dict:
    """Jalur keputusan hanya ada pada model berbasis pohon tunggal."""
    from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

    if not isinstance(model, (DecisionTreeClassifier, DecisionTreeRegressor)):
        output["unavailable"].append({
            "method": "decision_path",
            "reason": (
                "Jalur keputusan hanya tersedia untuk Decision Tree. "
                "Model ini bukan pohon tunggal."
            ),
        })

        return {}

    try:
        tree = model.tree_
        row = matrix.iloc[0]
        node = 0
        steps = []

        while tree.children_left[node] != tree.children_right[node]:
            feature = features[tree.feature[node]]
            threshold = float(tree.threshold[node])
            value = float(row[feature])
            goes_left = value <= threshold

            steps.append({
                "feature": feature,
                "value": value,
                "threshold": round(threshold, 4),
                "rule": f"{feature} {'≤' if goes_left else '>'} {threshold:.4f}",
            })

            node = tree.children_left[node] if goes_left else tree.children_right[node]

        leaf = tree.value[node][0]
        outcome = (
            classes[int(np.argmax(leaf))] if classes and len(classes) == len(leaf)
            else round(float(leaf[0]), 4)
        )

        output["available"].append("decision_path")

        return {
            "decision_path": {
                "row": 0,
                "depth": len(steps),
                "steps": steps,
                "outcome": outcome,
                "interpretation": (
                    f"Baris pertama melewati {len(steps)} percabangan sebelum "
                    f"model menyimpulkan {outcome}."
                ),
            }
        }
    except Exception as error:
        output["unavailable"].append({
            "method": "decision_path",
            "reason": f"Jalur keputusan gagal dibaca ({type(error).__name__}).",
        })

        return {}
