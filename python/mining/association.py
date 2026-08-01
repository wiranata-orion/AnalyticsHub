"""Association Rule: menemukan pola "yang sering muncul bersamaan".

Memakai Apriori dari mlxtend atas keranjang yang dibentuk dari kolom kategori.
Setiap baris dianggap satu transaksi, dan setiap nilai kategori menjadi itemnya.
"""

from __future__ import annotations

import pandas as pd

from core import loader
from core.io import EngineError

MAX_BASKET_COLUMNS = 5
MAX_UNIQUE = 20


def run(params: dict) -> dict:
    from mlxtend.frequent_patterns import apriori, association_rules

    frame = loader.load(params)

    columns = params.get("columns") or [
        name for name in loader.categorical_columns(frame, max_unique=MAX_UNIQUE)
    ][:MAX_BASKET_COLUMNS]

    if len(columns) < 2:
        raise EngineError(
            "Association rule butuh minimal dua kolom kategori berkardinalitas rendah."
        )

    subset = frame[columns].dropna(how="all")

    if subset.empty:
        raise EngineError("Tidak ada baris yang bisa dijadikan transaksi.")

    # Nilai diberi awalan nama kolom supaya "Bali" pada kolom wilayah tidak
    # tertukar dengan "Bali" pada kolom cabang.
    basket = pd.get_dummies(subset.astype(str), prefix_sep="=", dtype=bool)

    min_support = float(params.get("min_support", 0.05))
    min_confidence = float(params.get("min_confidence", 0.3))
    min_lift = float(params.get("min_lift", 1.0))

    frequent = apriori(basket, min_support=min_support, use_colnames=True, max_len=3)

    if frequent.empty:
        raise EngineError(
            f"Tidak ada kombinasi item yang mencapai support {min_support:.0%}. "
            "Turunkan ambang minimum support."
        )

    rules = association_rules(frequent, metric="confidence", min_threshold=min_confidence)

    if rules.empty:
        raise EngineError(
            f"Ada kombinasi yang sering muncul, tetapi tidak satu pun mencapai "
            f"confidence {min_confidence:.0%}. Turunkan ambangnya."
        )

    rules = rules[rules["lift"] >= min_lift].sort_values("lift", ascending=False).head(25)

    def render(items) -> str:
        return ", ".join(sorted(str(item) for item in items))

    return {
        "columns": columns,
        "transactions": int(len(basket)),
        "min_support": min_support,
        "min_confidence": min_confidence,
        "rules": [
            {
                "id": index,
                "antecedent": render(row["antecedents"]),
                "consequent": render(row["consequents"]),
                "support": round(float(row["support"]), 4),
                "confidence": round(float(row["confidence"]), 4),
                "lift": round(float(row["lift"]), 3),
                "interpretation": (
                    f"Muncul bersama {float(row['lift']):.1f}× lebih sering "
                    "daripada yang diharapkan secara kebetulan."
                ),
            }
            for index, (_, row) in enumerate(rules.iterrows(), start=1)
        ],
        "frequent_itemsets": [
            {"items": render(row["itemsets"]), "support": round(float(row["support"]), 4)}
            for _, row in frequent.sort_values("support", ascending=False).head(15).iterrows()
        ],
    }
