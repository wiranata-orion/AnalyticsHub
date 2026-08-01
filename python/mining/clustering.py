"""Clustering: mengelompokkan baris serupa tanpa label."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core import loader
from core.io import EngineError

MAX_COLUMNS = 6


def run(params: dict) -> dict:
    from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    frame = loader.load(params)
    columns = params.get("columns") or loader.numeric_columns(frame)[:MAX_COLUMNS]

    if len(columns) < 2:
        raise EngineError("Clustering butuh minimal dua kolom numerik.")

    subset = frame[columns].dropna()

    if len(subset) < 10:
        raise EngineError("Baris lengkap terlalu sedikit untuk dikelompokkan.")

    # Pembakuan wajib: tanpa itu kolom bersatuan rupiah mendominasi jarak
    # Euclidean dan kolom lain praktis diabaikan.
    scaled = StandardScaler().fit_transform(subset)

    algorithm = params.get("algorithm", "kmeans")
    k = int(params.get("k", 3))

    if algorithm == "dbscan":
        model = DBSCAN(eps=float(params.get("eps", 0.8)), min_samples=int(params.get("min_samples", 5)))
        labels = model.fit_predict(scaled)
        iterations = None
    elif algorithm == "hierarchical":
        model = AgglomerativeClustering(n_clusters=k)
        labels = model.fit_predict(scaled)
        iterations = None
    else:
        model = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = model.fit_predict(scaled)
        iterations = int(model.n_iter_)

    unique = sorted(set(labels))
    # DBSCAN menandai derau sebagai -1; itu bukan cluster dan tidak boleh ikut
    # dihitung dalam silhouette.
    real_clusters = [label for label in unique if label != -1]

    silhouette = None

    if len(real_clusters) >= 2:
        mask = labels != -1
        silhouette = float(silhouette_score(scaled[mask], labels[mask]))

    clusters = []

    for label in unique:
        members = subset[labels == label]
        clusters.append({
            "cluster": int(label),
            "label": "Derau" if label == -1 else f"Cluster {int(label) + 1}",
            "size": int(len(members)),
            "share": round(len(members) / len(subset) * 100, 2),
            "center": {name: round(float(members[name].mean()), 4) for name in columns},
        })

    axes = columns[:2]
    series = [
        {
            "label": cluster["label"],
            "data": [
                {"x": float(row[0]), "y": float(row[1])}
                for row in subset.loc[labels == cluster["cluster"], axes].itertuples(index=False)
            ],
        }
        for cluster in clusters
    ]

    # Elbow membantu pengguna menilai apakah k yang dipilih masuk akal.
    elbow = []

    if algorithm == "kmeans" and len(subset) >= 20:
        for candidate in range(2, min(9, len(subset))):
            trial = KMeans(n_clusters=candidate, n_init=5, random_state=42).fit(scaled)
            elbow.append({"k": candidate, "inertia": float(trial.inertia_)})

    return {
        "algorithm": algorithm,
        "columns": columns,
        "k": len(real_clusters),
        "iterations": iterations,
        "silhouette": silhouette,
        "clusters": clusters,
        "axes": axes,
        "series": series,
        "elbow": elbow,
        "interpretation": (
            f"Terbentuk {len(real_clusters)} kelompok"
            + (
                f" dengan skor silhouette {silhouette:.2f} "
                f"({'pemisahan jelas' if silhouette >= 0.5 else 'pemisahan cukup' if silhouette >= 0.25 else 'pemisahan lemah'})."
                if silhouette is not None else "."
            )
        ),
    }
