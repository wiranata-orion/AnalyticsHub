/*
 * Profiling dataset: menghitung karakteristik tiap kolom dari baris sungguhan.
 *
 * Padanan `python/core/profiler.py`. Selama engine Python belum tersambung,
 * perhitungannya dilakukan di peramban atas tabel dari `@/data/profiles`.
 * Seluruh halaman analisis membaca hasil profiling ini, jadi angka di grafik,
 * rekomendasi algoritma, dan pilihan target selalu berasal dari sumber yang sama.
 *
 * Kolom identitas (nilai unik untuk setiap baris) ditandai `isIdentifier` dan
 * dikecualikan dari analisis — mengorelasikan nomor transaksi tidak bermakna.
 */

export function mean(values) {
    return values.length
        ? values.reduce((sum, value) => sum + value, 0) / values.length
        : 0;
}

export function stdDev(values) {
    if (values.length < 2) {
        return 0;
    }

    const average = mean(values);
    const variance =
        values.reduce((sum, value) => sum + (value - average) ** 2, 0) /
        (values.length - 1);

    return Math.sqrt(variance);
}

/** Kuantil dengan interpolasi linear pada data yang sudah terurut. */
export function quantile(sorted, fraction) {
    if (!sorted.length) {
        return 0;
    }

    const position = (sorted.length - 1) * fraction;
    const lower = Math.floor(position);
    const upper = Math.ceil(position);

    if (lower === upper) {
        return sorted[lower];
    }

    return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
}

export function pearson(a, b) {
    const pairs = a
        .map((value, index) => [value, b[index]])
        .filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y));

    if (pairs.length < 3) {
        return 0;
    }

    const xs = pairs.map(([x]) => x);
    const ys = pairs.map(([, y]) => y);
    const meanX = mean(xs);
    const meanY = mean(ys);

    let numerator = 0;
    let sumX = 0;
    let sumY = 0;

    for (let index = 0; index < pairs.length; index += 1) {
        const dx = xs[index] - meanX;
        const dy = ys[index] - meanY;

        numerator += dx * dy;
        sumX += dx * dx;
        sumY += dy * dy;
    }

    const denominator = Math.sqrt(sumX * sumY);

    return denominator === 0 ? 0 : numerator / denominator;
}

export const isNumericType = (type) => type === 'integer' || type === 'float';

/** Angka panjang dipersingkat agar muat sebagai label sumbu. */
export function formatNumber(value) {
    if (!Number.isFinite(value)) {
        return '—';
    }

    const magnitude = Math.abs(value);

    if (magnitude >= 1_000_000_000) {
        return `${(value / 1_000_000_000).toFixed(1).replace('.', ',')} M`;
    }

    if (magnitude >= 1_000_000) {
        return `${(value / 1_000_000).toFixed(1).replace('.', ',')} jt`;
    }

    if (magnitude >= 10_000) {
        return `${Math.round(value / 1000).toLocaleString('id-ID')} rb`;
    }

    if (Number.isInteger(value)) {
        return value.toLocaleString('id-ID');
    }

    return value.toFixed(2).replace('.', ',');
}

function profileNumeric(values) {
    const sorted = [...values].sort((a, b) => a - b);
    const q1 = quantile(sorted, 0.25);
    const median = quantile(sorted, 0.5);
    const q3 = quantile(sorted, 0.75);
    const iqr = q3 - q1;

    // Batas Tukey 1,5 × IQR — ambang yang sama dipakai halaman Cleaning dan
    // algoritma anomali, supaya "outlier" berarti hal yang sama di seluruh aplikasi.
    const lowerFence = q1 - 1.5 * iqr;
    const upperFence = q3 + 1.5 * iqr;
    const outliers = sorted.filter(
        (value) => value < lowerFence || value > upperFence,
    );

    const min = sorted[0] ?? 0;
    const max = sorted[sorted.length - 1] ?? 0;
    const binCount = 8;
    const width = (max - min) / binCount || 1;
    const counts = new Array(binCount).fill(0);

    for (const value of sorted) {
        const index = Math.min(binCount - 1, Math.floor((value - min) / width));

        counts[index] += 1;
    }

    return {
        mean: mean(sorted),
        std: stdDev(sorted),
        min,
        max,
        q1,
        median,
        q3,
        lowerFence: Math.max(min, lowerFence),
        upperFence: Math.min(max, upperFence),
        outlierCount: outliers.length,
        outlierRatio: sorted.length ? outliers.length / sorted.length : 0,
        histogram: {
            labels: counts.map((_, index) => {
                const from = min + index * width;

                return `${formatNumber(from)}–${formatNumber(from + width)}`;
            }),
            counts,
        },
    };
}

function profileCategorical(values) {
    const tally = new Map();

    for (const value of values) {
        const key = String(value);

        tally.set(key, (tally.get(key) ?? 0) + 1);
    }

    const top = [...tally.entries()]
        .map(([value, count]) => ({
            value,
            count,
            share: values.length ? (count / values.length) * 100 : 0,
        }))
        .sort((a, b) => b.count - a.count);

    return { top };
}

function profileColumn(column, rows) {
    const raw = rows.map((row) => row[column.name]);
    const present = raw.filter((value) => value !== null && value !== undefined);
    const missingCount = raw.length - present.length;
    const unique = new Set(present.map((value) => String(value))).size;

    const base = {
        name: column.name,
        type: column.type,
        missingCount,
        missing: raw.length ? (missingCount / raw.length) * 100 : 0,
        unique,
        // Kolom teks yang seluruh nilainya unik adalah identitas baris, bukan
        // variabel yang bisa dianalisis.
        isIdentifier:
            column.type === 'text' && unique === present.length && unique > 1,
    };

    if (isNumericType(column.type)) {
        return { ...base, ...profileNumeric(present.map(Number)) };
    }

    if (column.type === 'category' || column.type === 'text') {
        return { ...base, ...profileCategorical(present) };
    }

    return base;
}

function countDuplicates(rows, columns) {
    // Kolom identitas diabaikan: dua baris dengan isi sama tetap duplikat
    // walaupun nomor transaksinya berbeda.
    const keys = columns
        .filter((column) => !column.isIdentifier)
        .map((column) => column.name);
    const seen = new Set();
    let duplicates = 0;

    for (const row of rows) {
        const signature = keys.map((key) => row[key]).join('');

        if (seen.has(signature)) {
            duplicates += 1;
        } else {
            seen.add(signature);
        }
    }

    return duplicates;
}

function buildCorrelation(rows, numericColumns) {
    const names = numericColumns.slice(0, 6).map((column) => column.name);
    const series = names.map((name) =>
        rows.map((row) => (row[name] === null ? NaN : Number(row[name]))),
    );

    return {
        columns: names,
        matrix: series.map((left) =>
            series.map((right) => Number(pearson(left, right).toFixed(2))),
        ),
    };
}

/**
 * Hasil profiling satu tabel.
 *
 * @returns {{ rowCount, columns, numeric, categorical, datetime, identifiers,
 *   correlation, duplicateRows, outlierRatio }}
 */
export function profileTable(table) {
    const columns = table.columns.map((column) =>
        profileColumn(column, table.rows),
    );

    const numeric = columns.filter(
        (column) => isNumericType(column.type) && !column.isIdentifier,
    );
    const categorical = columns.filter(
        (column) => column.type === 'category' && !column.isIdentifier,
    );
    const datetime = columns.filter((column) => column.type === 'datetime');
    const identifiers = columns.filter((column) => column.isIdentifier);

    const outlierTotal = numeric.reduce(
        (sum, column) => sum + column.outlierCount,
        0,
    );

    return {
        rowCount: table.rows.length,
        columns,
        numeric,
        categorical,
        datetime,
        identifiers,
        correlation: numeric.length >= 2 ? buildCorrelation(table.rows, numeric) : null,
        duplicateRows: countDuplicates(table.rows, columns),
        outlierRatio: numeric.length
            ? outlierTotal / (numeric.length * table.rows.length)
            : 0,
    };
}

/** Pasangan kolom numerik dengan korelasi absolut tertinggi. */
export function strongestPair(profile) {
    if (!profile.correlation) {
        return null;
    }

    const { columns, matrix } = profile.correlation;
    let best = null;

    for (let row = 0; row < columns.length; row += 1) {
        for (let col = row + 1; col < columns.length; col += 1) {
            const value = matrix[row][col];

            if (!best || Math.abs(value) > Math.abs(best.value)) {
                best = { x: columns[row], y: columns[col], value };
            }
        }
    }

    return best;
}
