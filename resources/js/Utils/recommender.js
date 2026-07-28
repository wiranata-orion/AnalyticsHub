/*
 * Rekomendasi algoritma dari karakteristik dataset.
 *
 * Padanan `python/core/recommender.py`. Alurnya: profil kolom -> karakteristik
 * -> daftar algoritma yang cocok beserta alasannya. Alasan selalu menyebut
 * kolom yang mendasarinya, supaya rekomendasi bisa ditelusuri pengguna dan tidak
 * terbaca sebagai tebakan.
 *
 * Rekomendasi tidak pernah membatasi pilihan — seluruh algoritma tetap bisa
 * dijalankan, yang direkomendasikan hanya ditandai dan diurutkan lebih dulu.
 */

// Kolom kategori dengan kardinalitas di atas ini lebih mirip identitas
// (kode pos, SKU) daripada label yang bisa diprediksi.
const MAX_TARGET_CLASSES = 8;

// Ambang lift untuk menyebut dua item "sering muncul bersama". Di bawah ini
// pasangannya tidak lebih sering daripada yang diharapkan secara kebetulan.
const BASKET_LIFT = 1.4;
const BASKET_SUPPORT = 0.05;

/*
 * Seberapa kuat nilai antar kolom kategori muncul bersama.
 *
 * Tanpa ukuran ini, "data transaksional" hanya berarti "punya kolom identitas
 * dan beberapa kolom kategori" — dan itu benar untuk hampir semua tabel,
 * sehingga Association Rule akan direkomendasikan di mana-mana. Yang menentukan
 * sebenarnya adalah ada tidaknya pasangan nilai yang benar-benar berulang
 * bersamaan.
 */
function basketStrength(table, columns) {
    if (columns.length < 2 || !table?.rows?.length) {
        return 0;
    }

    const total = table.rows.length;
    const singles = new Map();
    const pairs = new Map();

    for (const row of table.rows) {
        const items = columns
            .filter((column) => row[column] !== null && row[column] !== undefined)
            .map((column) => ({ column, value: `${column}=${row[column]}` }));

        for (const item of items) {
            singles.set(item.value, (singles.get(item.value) ?? 0) + 1);
        }

        for (let i = 0; i < items.length; i += 1) {
            for (let j = i + 1; j < items.length; j += 1) {
                const key = `${items[i].value}|${items[j].value}`;

                pairs.set(key, (pairs.get(key) ?? 0) + 1);
            }
        }
    }

    let highest = 0;

    for (const [key, count] of pairs.entries()) {
        const support = count / total;

        if (support < BASKET_SUPPORT) {
            continue;
        }

        const [left, right] = key.split('|');
        const expected =
            ((singles.get(left) ?? 0) / total) * ((singles.get(right) ?? 0) / total);
        const lift = expected ? support / expected : 0;

        highest = Math.max(highest, lift);
    }

    return highest;
}

/** Kandidat target: kategori berkardinalitas rendah dan numerik non-identitas. */
export function analyzeCharacteristics(profile, table) {
    const categoricalTargets = profile.categorical
        .filter(
            (column) => column.unique >= 2 && column.unique <= MAX_TARGET_CLASSES,
        )
        .sort((a, b) => a.unique - b.unique);

    // Kolom numerik yang berhubungan dengan kolom numerik lain lebih layak jadi
    // target regresi daripada kolom yang berdiri sendiri.
    const numericTargets = profile.numeric
        .map((column) => {
            const index = profile.correlation?.columns.indexOf(column.name) ?? -1;
            const strongest =
                index >= 0
                    ? Math.max(
                          ...profile.correlation.matrix[index].map((value, other) =>
                              other === index ? 0 : Math.abs(value),
                          ),
                      )
                    : 0;

            return { column, strongest };
        })
        .sort((a, b) => b.strongest - a.strongest);

    const basketColumns = profile.categorical.filter(
        (column) => column.unique >= 2 && column.unique <= 12,
    );

    const basketLift = basketStrength(
        table,
        basketColumns.map((column) => column.name),
    );

    return {
        basketLift,
        rowCount: profile.rowCount,
        numericCount: profile.numeric.length,
        categoricalCount: profile.categorical.length,
        datetimeCount: profile.datetime.length,
        hasIdentifier: profile.identifiers.length > 0,
        outlierRatio: profile.outlierRatio,
        duplicateRows: profile.duplicateRows,
        categoricalTargets,
        numericTargets,
        basketColumns,
        // Dataset transaksional: ada nomor identitas per baris, minimal dua
        // kolom "item", DAN pasangan nilainya memang berulang bersamaan.
        isTransactional:
            profile.identifiers.length > 0 &&
            basketColumns.length >= 2 &&
            basketLift >= BASKET_LIFT,
    };
}

const percent = (value) => `${(value * 100).toFixed(1).replace('.', ',')}%`;

/**
 * @returns {Array<{ key, level: 'high'|'medium', reason }>} urut dari yang
 *   paling sesuai.
 */
export function recommendAlgorithms(profile, table) {
    const facts = analyzeCharacteristics(profile, table);
    const recommendations = [];

    const categoricalTarget = facts.categoricalTargets[0];
    const numericTarget = facts.numericTargets[0];

    if (categoricalTarget) {
        recommendations.push({
            key: 'classification',
            level: 'high',
            reason: `Kolom "${categoricalTarget.name}" berisi ${categoricalTarget.unique} kelas — cocok dijadikan target klasifikasi.`,
        });
    }

    if (numericTarget && numericTarget.strongest >= 0.4) {
        recommendations.push({
            key: 'regression',
            level: 'high',
            reason: `Kolom "${numericTarget.column.name}" berkorelasi ${numericTarget.strongest
                .toFixed(2)
                .replace('.', ',')} dengan kolom numerik lain — nilainya dapat diprediksi.`,
        });
    } else if (numericTarget) {
        recommendations.push({
            key: 'regression',
            level: 'medium',
            reason: `Ada ${facts.numericCount} kolom numerik, tetapi korelasi antar kolom masih lemah.`,
        });
    }

    if (facts.datetimeCount > 0 && facts.numericCount > 0) {
        recommendations.push({
            key: 'timeseries',
            level: 'high',
            reason: `Kolom waktu "${profile.datetime[0].name}" tersedia, sehingga nilai numerik bisa dianalisis sebagai deret waktu.`,
        });
    }

    if (facts.isTransactional) {
        recommendations.push({
            key: 'association',
            level: 'high',
            reason: `Berbentuk transaksi: ${facts.basketColumns.length} kolom item, dengan pasangan nilai yang muncul bersama ${facts.basketLift
                .toFixed(1)
                .replace('.', ',')}× lebih sering daripada kebetulan.`,
        });
    }

    if (facts.outlierRatio >= 0.02) {
        recommendations.push({
            key: 'anomaly',
            level: 'high',
            reason: `${percent(facts.outlierRatio)} nilai numerik berada di luar batas wajar — jumlah nilai ekstremnya menonjol.`,
        });
    } else {
        recommendations.push({
            key: 'anomaly',
            level: 'medium',
            reason: `Nilai ekstrem hanya ${percent(facts.outlierRatio)} dari data, anomali kemungkinan sedikit.`,
        });
    }

    if (!categoricalTarget) {
        recommendations.push({
            key: 'clustering',
            level: 'high',
            reason: 'Tidak ada kolom target yang jelas — pengelompokan tanpa label paling masuk akal.',
        });
    } else if (facts.numericCount >= 2) {
        recommendations.push({
            key: 'clustering',
            level: 'medium',
            reason: `Ada ${facts.numericCount} kolom numerik yang bisa dikelompokkan sebagai segmentasi tambahan.`,
        });
    }

    const order = { high: 0, medium: 1 };

    return recommendations.sort((a, b) => order[a.level] - order[b.level]);
}
