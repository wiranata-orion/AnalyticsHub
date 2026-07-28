/*
 * Algoritma data mining tanpa label: clustering, association rule, deteksi
 * anomali, dan analisis deret waktu.
 *
 * Padanan `python/mining/{clustering,association,anomaly,timeseries}.py`.
 * Semua berjalan atas baris dataset sungguhan sehingga hasilnya berubah ketika
 * dataset yang dipilih berganti.
 */

import { aggregate, dateKey, dateLabel, suggestGrain } from '@/Utils/chartBuilder';
import { mean, quantile, stdDev } from '@/Utils/profiler';

// ---------------------------------------------------------------------------
// Clustering — K-Means
// ---------------------------------------------------------------------------

/*
 * Fitur dibakukan lebih dulu (z-score). Tanpa itu kolom bersatuan besar seperti
 * rupiah akan mendominasi jarak Euclidean dan kolom lain praktis diabaikan.
 */
function standardize(rows, columns) {
    const stats = columns.map((column) => {
        const values = rows.map((row) => Number(row[column]));

        return { mean: mean(values), std: stdDev(values) || 1 };
    });

    return {
        stats,
        vectors: rows.map((row) =>
            columns.map(
                (column, index) =>
                    (Number(row[column]) - stats[index].mean) / stats[index].std,
            ),
        ),
    };
}

const distance = (a, b) =>
    a.reduce((sum, value, index) => sum + (value - b[index]) ** 2, 0);

export function runClustering({ table, profile, k = 3, maxIterations = 60 }) {
    const columns = profile.numeric.slice(0, 4).map((column) => column.name);

    if (columns.length < 2) {
        return { ok: false, message: 'Clustering butuh minimal dua kolom numerik.' };
    }

    const rows = table.rows.filter((row) =>
        columns.every((column) => Number.isFinite(Number(row[column]))),
    );

    if (rows.length < k * 3) {
        return { ok: false, message: 'Baris lengkap terlalu sedikit untuk dikelompokkan.' };
    }

    const { vectors, stats } = standardize(rows, columns);

    // Inisialisasi k-means++ sederhana: pusat pertama diambil dari titik paling
    // awal, berikutnya dari titik terjauh terhadap pusat yang sudah ada.
    const centroids = [vectors[0]];

    while (centroids.length < k) {
        let farthest = vectors[0];
        let best = -1;

        for (const vector of vectors) {
            const nearest = Math.min(
                ...centroids.map((centroid) => distance(vector, centroid)),
            );

            if (nearest > best) {
                best = nearest;
                farthest = vector;
            }
        }

        centroids.push(farthest);
    }

    let assignments = new Array(vectors.length).fill(0);
    let iterations = 0;

    for (; iterations < maxIterations; iterations += 1) {
        let moved = false;

        vectors.forEach((vector, index) => {
            let bestCluster = 0;
            let bestDistance = Infinity;

            centroids.forEach((centroid, cluster) => {
                const value = distance(vector, centroid);

                if (value < bestDistance) {
                    bestDistance = value;
                    bestCluster = cluster;
                }
            });

            if (assignments[index] !== bestCluster) {
                assignments[index] = bestCluster;
                moved = true;
            }
        });

        for (let cluster = 0; cluster < k; cluster += 1) {
            const members = vectors.filter(
                (_, index) => assignments[index] === cluster,
            );

            if (members.length) {
                centroids[cluster] = columns.map((__, dimension) =>
                    mean(members.map((member) => member[dimension])),
                );
            }
        }

        if (!moved) {
            break;
        }
    }

    const inertia = vectors.reduce(
        (sum, vector, index) => sum + distance(vector, centroids[assignments[index]]),
        0,
    );

    const clusters = centroids.map((centroid, cluster) => {
        const size = assignments.filter((value) => value === cluster).length;

        return {
            cluster: cluster + 1,
            size,
            share: (size / rows.length) * 100,
            // Pusat dikembalikan ke satuan asli agar bisa dibaca pengguna.
            center: columns.map((column, index) =>
                Number(
                    (centroid[index] * stats[index].std + stats[index].mean).toFixed(2),
                ),
            ),
        };
    });

    return {
        ok: true,
        columns,
        k,
        iterations,
        inertia: Number(inertia.toFixed(2)),
        clusters,
        // Dua kolom pertama dipakai sebagai proyeksi agar hasilnya bisa dilihat
        // sebagai scatter dua dimensi.
        axes: [columns[0], columns[1]],
        series: clusters.map((cluster) => ({
            label: `Cluster ${cluster.cluster}`,
            data: rows
                .filter((_, index) => assignments[index] === cluster.cluster - 1)
                .map((row) => ({
                    x: Number(row[columns[0]]),
                    y: Number(row[columns[1]]),
                })),
        })),
    };
}

// ---------------------------------------------------------------------------
// Association Rule — Apriori untuk pasangan item
// ---------------------------------------------------------------------------

export function runAssociation({
    table,
    profile,
    minSupport = 0.05,
    minConfidence = 0.35,
}) {
    const columns = profile.categorical
        .filter((column) => column.unique >= 2 && column.unique <= 12)
        .slice(0, 4)
        .map((column) => column.name);

    if (columns.length < 2) {
        return {
            ok: false,
            message: 'Association rule butuh minimal dua kolom kategori.',
        };
    }

    const baskets = table.rows.map((row) =>
        columns
            .filter((column) => row[column] !== null && row[column] !== undefined)
            .map((column) => ({ column, item: String(row[column]) })),
    );

    const total = baskets.length || 1;
    const singles = new Map();

    for (const basket of baskets) {
        for (const entry of basket) {
            singles.set(entry.item, (singles.get(entry.item) ?? 0) + 1);
        }
    }

    const pairs = new Map();

    for (const basket of baskets) {
        for (let i = 0; i < basket.length; i += 1) {
            for (let j = 0; j < basket.length; j += 1) {
                // Dua nilai dari kolom yang sama saling meniadakan (satu baris
                // hanya punya satu wilayah), jadi pasangannya tidak bermakna.
                if (i === j || basket[i].column === basket[j].column) {
                    continue;
                }

                const key = `${basket[i].item}→${basket[j].item}`;

                pairs.set(key, (pairs.get(key) ?? 0) + 1);
            }
        }
    }

    const rules = [];

    for (const [key, count] of pairs.entries()) {
        const [antecedent, consequent] = key.split('→');
        const support = count / total;
        const confidence = count / (singles.get(antecedent) || 1);
        const consequentSupport = (singles.get(consequent) || 1) / total;
        const lift = confidence / consequentSupport;

        if (support >= minSupport && confidence >= minConfidence && lift > 1) {
            rules.push({
                id: key,
                antecedent,
                consequent,
                support: support.toFixed(3).replace('.', ','),
                confidence: confidence.toFixed(3).replace('.', ','),
                lift: lift.toFixed(2).replace('.', ','),
                liftValue: lift,
            });
        }
    }

    return {
        ok: true,
        columns,
        transactions: total,
        rules: rules.sort((a, b) => b.liftValue - a.liftValue).slice(0, 12),
        minSupport,
        minConfidence,
    };
}

// ---------------------------------------------------------------------------
// Anomaly Detection — batas Tukey + skor z gabungan
// ---------------------------------------------------------------------------

export function runAnomaly({ table, profile, threshold = 3 }) {
    const columns = profile.numeric.slice(0, 5).map((column) => column.name);

    if (!columns.length) {
        return { ok: false, message: 'Deteksi anomali butuh kolom numerik.' };
    }

    const rows = table.rows.filter((row) =>
        columns.every((column) => Number.isFinite(Number(row[column]))),
    );

    const bounds = columns.map((column) => {
        const values = rows.map((row) => Number(row[column])).sort((a, b) => a - b);
        const q1 = quantile(values, 0.25);
        const q3 = quantile(values, 0.75);
        const iqr = q3 - q1;

        return {
            column,
            lower: q1 - 1.5 * iqr,
            upper: q3 + 1.5 * iqr,
            mean: mean(values),
            std: stdDev(values) || 1,
        };
    });

    const scored = rows.map((row) => {
        // Skor = simpangan baku terbesar di antara kolom; kolom penyebabnya
        // ikut dicatat supaya hasilnya bisa dijelaskan, bukan sekadar ditandai.
        let score = 0;
        let cause = columns[0];

        for (const bound of bounds) {
            const value = Number(row[bound.column]);
            const z = Math.abs((value - bound.mean) / bound.std);

            if (z > score) {
                score = z;
                cause = bound.column;
            }
        }

        const outOfRange = bounds.some((bound) => {
            const value = Number(row[bound.column]);

            return value < bound.lower || value > bound.upper;
        });

        return {
            row,
            score: Number(score.toFixed(2)),
            cause,
            isAnomaly: outOfRange && score >= threshold,
        };
    });

    const anomalies = scored.filter((item) => item.isAnomaly);
    const axes = [columns[0], columns[1] ?? columns[0]];

    return {
        ok: true,
        columns,
        threshold,
        checked: rows.length,
        count: anomalies.length,
        ratio: rows.length ? anomalies.length / rows.length : 0,
        top: anomalies
            .sort((a, b) => b.score - a.score)
            .slice(0, 10)
            .map((item, index) => ({
                id: index + 1,
                cause: item.cause,
                score: item.score.toFixed(2).replace('.', ','),
                value: Number(item.row[item.cause]).toLocaleString('id-ID'),
                context: axes
                    .map((axis) => `${axis}: ${Number(item.row[axis]).toLocaleString('id-ID')}`)
                    .join(' · '),
            })),
        axes,
        series: [
            {
                label: 'Normal',
                data: scored
                    .filter((item) => !item.isAnomaly)
                    .map((item) => ({
                        x: Number(item.row[axes[0]]),
                        y: Number(item.row[axes[1]]),
                    })),
            },
            {
                label: 'Anomali',
                data: anomalies.map((item) => ({
                    x: Number(item.row[axes[0]]),
                    y: Number(item.row[axes[1]]),
                })),
            },
        ],
    };
}

// ---------------------------------------------------------------------------
// Time Series — agregasi periode, rata-rata bergerak, proyeksi linear
// ---------------------------------------------------------------------------

export function runTimeSeries({ table, profile, horizon = 6 }) {
    const timeColumn = profile.datetime[0];
    const valueColumn = profile.numeric[0];

    if (!timeColumn || !valueColumn) {
        return {
            ok: false,
            message: 'Analisis deret waktu butuh satu kolom waktu dan satu kolom numerik.',
        };
    }

    const grain = suggestGrain(table.rows.map((row) => row[timeColumn.name]));
    const buckets = new Map();

    for (const row of table.rows) {
        const key = dateKey(row[timeColumn.name], grain);
        const value = Number(row[valueColumn.name]);

        if (!key || !Number.isFinite(value)) {
            continue;
        }

        if (!buckets.has(key)) {
            buckets.set(key, []);
        }

        buckets.get(key).push(value);
    }

    const keys = [...buckets.keys()].sort();

    if (keys.length < 4) {
        return { ok: false, message: 'Periode waktu terlalu sedikit untuk dianalisis.' };
    }

    const values = keys.map((key) =>
        Number(aggregate(buckets.get(key), 'avg').toFixed(2)),
    );

    const window = Math.max(3, Math.round(values.length / 8));
    const movingAverage = values.map((_, index) =>
        Number(
            aggregate(
                values.slice(Math.max(0, index - window + 1), index + 1),
                'avg',
            ).toFixed(2),
        ),
    );

    // Proyeksi memakai garis tren kuadrat terkecil atas indeks periode.
    const indices = values.map((_, index) => index);
    const meanIndex = mean(indices);
    const meanValue = mean(values);
    const slope =
        indices.reduce(
            (sum, index) => sum + (index - meanIndex) * (values[index] - meanValue),
            0,
        ) / (indices.reduce((sum, index) => sum + (index - meanIndex) ** 2, 0) || 1);
    const intercept = meanValue - slope * meanIndex;

    const forecast = Array.from({ length: horizon }, (_, step) =>
        Number((intercept + slope * (values.length + step)).toFixed(2)),
    );

    const labels = [
        ...keys.map((key) => dateLabel(key, grain)),
        ...forecast.map((_, step) => `+${step + 1}`),
    ];
    const padding = new Array(values.length).fill(null);

    return {
        ok: true,
        timeColumn: timeColumn.name,
        valueColumn: valueColumn.name,
        grain,
        window,
        horizon,
        slope,
        direction: slope >= 0 ? 'naik' : 'turun',
        periods: keys.length,
        labels,
        series: [
            {
                label: valueColumn.name,
                data: [...values, ...new Array(horizon).fill(null)],
            },
            {
                label: `Rata-rata bergerak ${window} periode`,
                data: [...movingAverage, ...new Array(horizon).fill(null)],
            },
            {
                label: 'Proyeksi',
                data: [...padding.slice(0, values.length - 1), values[values.length - 1], ...forecast],
            },
        ],
    };
}
