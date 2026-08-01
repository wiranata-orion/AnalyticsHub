"""Auto Insight: temuan otomatis dalam kalimat, bukan sekadar angka.

Setiap temuan berisi judul singkat, penjelasan satu kalimat, dan nada (baik,
perhatian, serius) supaya bisa langsung ditampilkan tanpa pengolahan lagi di
frontend.

Insight hanya dikeluarkan bila ada sesuatu yang layak diberitahukan. Menampilkan
"tidak ada missing value" untuk setiap kolom yang bersih hanya akan menenggelamkan
temuan yang benar-benar penting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core import loader

MISSING_ALERT = 5.0
STRONG_CORRELATION = 0.6
IMBALANCE_ALERT = 80.0
OUTLIER_ALERT = 3.0


def run(params: dict) -> dict:
    frame = loader.load(params)
    insights = []

    insights += _quality_insights(frame)
    insights += _correlation_insights(frame)
    insights += _category_insights(frame)
    insights += _numeric_insights(frame)
    insights += _time_insights(frame)

    order = {"serious": 0, "warning": 1, "good": 2, "info": 3}
    insights.sort(key=lambda item: order.get(item["tone"], 4))

    if not insights:
        insights.append({
            "tone": "good",
            "title": "Dataset dalam kondisi baik",
            "body": "Tidak ditemukan masalah kelengkapan, keseimbangan, maupun nilai ekstrem yang menonjol.",
        })

    return {
        "row_count": int(len(frame)),
        "column_count": int(frame.shape[1]),
        "insights": insights[:15],
    }


def _quality_insights(frame: pd.DataFrame) -> list:
    found = []
    cells = frame.shape[0] * frame.shape[1]

    if cells:
        missing_share = frame.isna().sum().sum() / cells * 100

        if missing_share >= MISSING_ALERT:
            worst = frame.isna().mean().idxmax()
            found.append({
                "tone": "warning",
                "title": f"Missing value sebesar {missing_share:.1f}%",
                "body": (
                    f'Kekosongan terbanyak ada pada kolom "{worst}" '
                    f"({frame[worst].isna().mean() * 100:.1f}% baris). "
                    "Tangani lebih dulu di menu Data Cleaning sebelum melatih model."
                ),
            })
        elif missing_share == 0:
            found.append({
                "tone": "good",
                "title": "Dataset terisi lengkap",
                "body": "Tidak ada satu pun sel kosong, sehingga seluruh baris dapat dipakai untuk analisis.",
            })

    comparable = [name for name in frame.columns if not loader.is_identifier(frame[name])]
    duplicates = int(frame.duplicated(subset=comparable or None).sum())

    if duplicates:
        found.append({
            "tone": "warning",
            "title": f"{duplicates} baris duplikat ditemukan",
            "body": (
                f"Sebanyak {duplicates} baris ({duplicates / len(frame) * 100:.1f}%) "
                "identik dengan baris lain dan berpotensi menggandakan bobot data yang sama."
            ),
        })

    return found


def _correlation_insights(frame: pd.DataFrame) -> list:
    numeric = loader.numeric_columns(frame)

    if len(numeric) < 2:
        return []

    matrix = frame[numeric].corr(numeric_only=True)
    found = []

    for i, left in enumerate(numeric):
        for right in numeric[i + 1:]:
            value = matrix.loc[left, right]

            if pd.isna(value) or abs(value) < STRONG_CORRELATION:
                continue

            found.append({
                "tone": "info",
                "title": f'"{left}" dan "{right}" berkorelasi {value:.2f}',
                "body": (
                    f"Saat {left} naik, {right} cenderung "
                    f"{'ikut naik' if value > 0 else 'turun'}. "
                    "Hubungan sekuat ini biasanya berguna untuk model prediksi."
                ),
            })

    found.sort(key=lambda item: item["title"], reverse=True)

    return found[:3]


def _category_insights(frame: pd.DataFrame) -> list:
    found = []

    for name in loader.categorical_columns(frame)[:6]:
        values = frame[name].dropna().astype(str)

        if values.empty:
            continue

        counts = values.value_counts()
        top_label = counts.index[0]
        share = counts.iloc[0] / len(values) * 100

        if share >= IMBALANCE_ALERT:
            found.append({
                "tone": "warning",
                "title": f'Kolom "{name}" sangat tidak seimbang',
                "body": (
                    f'Nilai "{top_label}" mengisi {share:.1f}% baris. '
                    "Model klasifikasi pada kolom seperti ini cenderung hanya menebak kelas mayoritas."
                ),
            })
        elif len(counts) >= 2:
            found.append({
                "tone": "info",
                "title": f'"{top_label}" mendominasi kolom {name}',
                "body": (
                    f"Menguasai {share:.1f}% baris, diikuti "
                    f'"{counts.index[1]}" ({counts.iloc[1] / len(values) * 100:.1f}%).'
                ),
            })

    return found[:4]


def _numeric_insights(frame: pd.DataFrame) -> list:
    found = []

    for name in loader.numeric_columns(frame)[:8]:
        values = frame[name].dropna()

        if len(values) < 8:
            continue

        q1, q3 = values.quantile(0.25), values.quantile(0.75)
        iqr = q3 - q1
        outliers = int(((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).sum())
        share = outliers / len(values) * 100

        if share >= OUTLIER_ALERT:
            found.append({
                "tone": "serious",
                "title": f'Kolom "{name}" punya {outliers} nilai ekstrem',
                "body": (
                    f"Sebanyak {share:.1f}% nilainya berada di luar batas wajar "
                    f"(di bawah {q1 - 1.5 * iqr:.2f} atau di atas {q3 + 1.5 * iqr:.2f}). "
                    "Periksa apakah ini kesalahan pencatatan atau kejadian nyata."
                ),
            })
            continue

        skew = values.skew()

        if abs(skew) > 1.5:
            found.append({
                "tone": "info",
                "title": f'Sebaran "{name}" sangat miring',
                "body": (
                    f"Kemiringan {skew:.2f} menandakan sebagian kecil nilai jauh lebih "
                    f"{'besar' if skew > 0 else 'kecil'} daripada sisanya. "
                    "Median lebih mewakili data ini daripada rata-rata."
                ),
            })

    return found[:4]


def _time_insights(frame: pd.DataFrame) -> list:
    time_columns = loader.datetime_columns(frame)
    numeric = loader.numeric_columns(frame)

    if not time_columns or not numeric:
        return []

    time_column, value_column = time_columns[0], numeric[0]
    pair = frame[[time_column, value_column]].dropna().sort_values(time_column)

    if len(pair) < 6:
        return []

    positions = np.arange(len(pair))
    slope = np.polyfit(positions, pair[value_column].to_numpy(), 1)[0]

    first = pair[value_column].iloc[: max(1, len(pair) // 4)].mean()
    last = pair[value_column].iloc[-max(1, len(pair) // 4):].mean()

    if not first:
        return []

    change = (last - first) / abs(first) * 100

    if abs(change) < 5:
        return [{
            "tone": "info",
            "title": f'"{value_column}" relatif stabil sepanjang waktu',
            "body": f"Perubahan antara awal dan akhir periode hanya {change:+.1f}%.",
        }]

    return [{
        "tone": "good" if change > 0 else "warning",
        "title": f'"{value_column}" {"meningkat" if change > 0 else "menurun"} {abs(change):.1f}%',
        "body": (
            f"Rata-rata di akhir periode {last:,.2f} dibanding {first:,.2f} di awal, "
            f"berdasarkan kolom waktu \"{time_column}\"."
        ),
    }]
