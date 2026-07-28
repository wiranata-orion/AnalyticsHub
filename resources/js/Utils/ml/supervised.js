/*
 * Model terbimbing: klasifikasi dan regresi.
 *
 * Padanan `python/mining/classification.py` dan `python/mining/regression.py`.
 * Implementasinya sengaja ringkas — dataset di aplikasi ini berukuran ratusan
 * baris, jadi pelatihan selesai dalam hitungan milidetik di peramban dan halaman
 * tidak perlu menunggu job di server.
 *
 * Yang penting di sini bukan kecanggihan algoritmanya, melainkan bahwa evaluasi
 * benar-benar dihitung dari prediksi model pada data uji yang terpisah dari data
 * latih. Saat engine Python tersambung, hanya `trainModel()` yang berpindah
 * menjadi panggilan API; bentuk hasilnya sudah disamakan.
 */

import { isNumericType, mean, stdDev } from '@/Utils/profiler';
import {
    classificationMetrics,
    regressionMetrics,
    rocCurve,
} from '@/Utils/ml/metrics';

export const ALGORITHM_OPTIONS = {
    classification: [
        { value: 'naive-bayes', label: 'Gaussian Naive Bayes' },
        { value: 'knn', label: 'K-Nearest Neighbors (k=5)' },
    ],
    regression: [
        { value: 'ols', label: 'Linear Regression (OLS)' },
        { value: 'ridge', label: 'Ridge Regression' },
    ],
};

const ALGORITHM_LABEL = Object.fromEntries(
    Object.values(ALGORITHM_OPTIONS)
        .flat()
        .map((option) => [option.value, option.label]),
);

/** Pembagian latih/uji acak namun deterministik terhadap `seed`. */
export function trainTestSplit(rows, testRatio = 0.2, seed = 42) {
    let state = seed >>> 0;
    const shuffled = [...rows];

    for (let index = shuffled.length - 1; index > 0; index -= 1) {
        state = (state * 1664525 + 1013904223) >>> 0;

        const swap = state % (index + 1);

        [shuffled[index], shuffled[swap]] = [shuffled[swap], shuffled[index]];
    }

    const testSize = Math.max(1, Math.round(shuffled.length * testRatio));

    return {
        train: shuffled.slice(testSize),
        test: shuffled.slice(0, testSize),
    };
}

const usable = (row, features, target) =>
    row[target] !== null &&
    row[target] !== undefined &&
    features.every((feature) => row[feature] !== null && row[feature] !== undefined);

function softmax(scores) {
    const highest = Math.max(...scores.map((item) => item.score));
    const weights = scores.map((item) => ({
        label: item.label,
        weight: Math.exp(item.score - highest),
    }));
    const total = weights.reduce((sum, item) => sum + item.weight, 0) || 1;

    return new Map(weights.map((item) => [item.label, item.weight / total]));
}

// ---------------------------------------------------------------------------
// Klasifikasi — Gaussian Naive Bayes
// ---------------------------------------------------------------------------

function fitNaiveBayes(rows, features, target, types) {
    const labels = [...new Set(rows.map((row) => row[target]))].sort();
    const priors = new Map();
    const stats = new Map();

    for (const label of labels) {
        const subset = rows.filter((row) => row[target] === label);

        priors.set(label, subset.length / rows.length);

        const perFeature = new Map();

        for (const feature of features) {
            if (isNumericType(types[feature])) {
                const values = subset.map((row) => Number(row[feature]));
                const average = mean(values);
                const variance =
                    values.reduce((sum, value) => sum + (value - average) ** 2, 0) /
                    (values.length || 1);

                // Varians minimum menjaga pembagian tetap stabil saat sebuah
                // fitur konstan di dalam satu kelas.
                perFeature.set(feature, {
                    kind: 'numeric',
                    mean: average,
                    variance: Math.max(variance, 1e-6),
                });
            } else {
                const tally = new Map();

                for (const row of subset) {
                    const key = String(row[feature]);

                    tally.set(key, (tally.get(key) ?? 0) + 1);
                }

                perFeature.set(feature, {
                    kind: 'category',
                    tally,
                    total: subset.length,
                });
            }
        }

        stats.set(label, perFeature);
    }

    const distinctValues = new Map(
        features.map((feature) => [
            feature,
            new Set(rows.map((row) => String(row[feature]))).size,
        ]),
    );

    // Log-likelihood dipakai agar perkalian peluang tidak menyusut ke nol.
    function logLikelihood(row, label) {
        let total = Math.log(priors.get(label) || 1e-9);

        for (const feature of features) {
            const stat = stats.get(label).get(feature);

            if (stat.kind === 'numeric') {
                const value = Number(row[feature]);

                total +=
                    -((value - stat.mean) ** 2) / (2 * stat.variance) -
                    0.5 * Math.log(2 * Math.PI * stat.variance);
            } else {
                // Penghalusan Laplace: nilai kategori yang tak pernah muncul di
                // data latih tidak boleh membuat peluang kelas jadi nol.
                const count = stat.tally.get(String(row[feature])) ?? 0;
                const classes = distinctValues.get(feature) || 1;

                total += Math.log((count + 1) / (stat.total + classes));
            }
        }

        return total;
    }

    const posterior = (row) =>
        softmax(labels.map((label) => ({ label, score: logLikelihood(row, label) })));

    return {
        labels,
        predict: (row) =>
            [...posterior(row).entries()].sort((a, b) => b[1] - a[1])[0][0],
        probability: (row, label) => posterior(row).get(label) ?? 0,
    };
}

// ---------------------------------------------------------------------------
// Klasifikasi — K-Nearest Neighbors
// ---------------------------------------------------------------------------

function fitKnn(rows, features, target, types, k = 5) {
    const labels = [...new Set(rows.map((row) => row[target]))].sort();

    // Fitur numerik dibakukan agar kolom bersatuan besar tidak mendominasi
    // jarak; fitur kategori menyumbang 1 saat nilainya berbeda.
    const scales = Object.fromEntries(
        features
            .filter((feature) => isNumericType(types[feature]))
            .map((feature) => {
                const values = rows.map((row) => Number(row[feature]));

                return [feature, { mean: mean(values), std: stdDev(values) || 1 }];
            }),
    );

    const distance = (a, b) =>
        features.reduce((sum, feature) => {
            if (scales[feature]) {
                const left = (Number(a[feature]) - scales[feature].mean) / scales[feature].std;
                const right = (Number(b[feature]) - scales[feature].mean) / scales[feature].std;

                return sum + (left - right) ** 2;
            }

            return sum + (String(a[feature]) === String(b[feature]) ? 0 : 1);
        }, 0);

    function votes(row) {
        const nearest = rows
            .map((candidate) => ({
                label: candidate[target],
                distance: distance(row, candidate),
            }))
            .sort((a, b) => a.distance - b.distance)
            .slice(0, Math.min(k, rows.length));

        const tally = new Map(labels.map((label) => [label, 0]));

        for (const neighbour of nearest) {
            tally.set(neighbour.label, (tally.get(neighbour.label) ?? 0) + 1);
        }

        return { tally, total: nearest.length || 1 };
    }

    return {
        labels,
        predict: (row) => {
            const { tally } = votes(row);

            return [...tally.entries()].sort((a, b) => b[1] - a[1])[0][0];
        },
        probability: (row, label) => {
            const { tally, total } = votes(row);

            return (tally.get(label) ?? 0) / total;
        },
    };
}

// ---------------------------------------------------------------------------
// Regresi — kuadrat terkecil, dengan opsi penalti ridge
// ---------------------------------------------------------------------------

function solve(matrix, vector) {
    const size = vector.length;
    const augmented = matrix.map((row, index) => [...row, vector[index]]);

    for (let pivot = 0; pivot < size; pivot += 1) {
        let best = pivot;

        for (let row = pivot + 1; row < size; row += 1) {
            if (Math.abs(augmented[row][pivot]) > Math.abs(augmented[best][pivot])) {
                best = row;
            }
        }

        [augmented[pivot], augmented[best]] = [augmented[best], augmented[pivot]];

        const head = augmented[pivot][pivot];

        if (Math.abs(head) < 1e-12) {
            continue;
        }

        for (let row = 0; row < size; row += 1) {
            if (row === pivot) {
                continue;
            }

            const factor = augmented[row][pivot] / head;

            for (let col = pivot; col <= size; col += 1) {
                augmented[row][col] -= factor * augmented[pivot][col];
            }
        }
    }

    return augmented.map((row, index) =>
        Math.abs(row[index]) < 1e-12 ? 0 : row[size] / row[index],
    );
}

/*
 * Fitur dibakukan sebelum diselesaikan lalu koefisiennya dikembalikan ke satuan
 * asli. Pembakuan membuat penalti ridge berlaku adil untuk semua fitur — tanpa
 * itu kolom bersatuan rupiah akan dihukum jauh lebih keras daripada kolom
 * bersatuan satuan kecil, hanya karena skalanya berbeda.
 */
function fitLinearRegression(rows, features, target, alpha = 0) {
    const scales = features.map((feature) => {
        const values = rows.map((row) => Number(row[feature]));

        return { mean: mean(values), std: stdDev(values) || 1 };
    });

    const design = rows.map((row) => [
        1,
        ...features.map(
            (feature, index) =>
                (Number(row[feature]) - scales[index].mean) / scales[index].std,
        ),
    ]);
    const values = rows.map((row) => Number(row[target]));
    const size = features.length + 1;

    const normal = Array.from({ length: size }, (_, i) =>
        Array.from({ length: size }, (_, j) =>
            design.reduce((sum, row) => sum + row[i] * row[j], 0),
        ),
    );
    const moment = Array.from({ length: size }, (_, i) =>
        design.reduce((sum, row, index) => sum + row[i] * values[index], 0),
    );

    // Intersep tidak ikut dihukum; nilai kecil tetap ditambahkan agar matriks
    // tetap dapat diselesaikan ketika dua fitur nyaris kolinear.
    for (let index = 0; index < size; index += 1) {
        normal[index][index] += index === 0 ? 1e-8 : alpha + 1e-8;
    }

    const standardized = solve(normal, moment);
    const coefficients = features.map(
        (feature, index) => standardized[index + 1] / scales[index].std,
    );
    const intercept = features.reduce(
        (value, _, index) => value - coefficients[index] * scales[index].mean,
        standardized[0],
    );

    return {
        intercept,
        coefficients: features.map((feature, index) => ({
            feature,
            value: coefficients[index],
        })),
        predict: (row) =>
            intercept +
            features.reduce(
                (sum, feature, index) => sum + coefficients[index] * Number(row[feature]),
                0,
            ),
    };
}

// ---------------------------------------------------------------------------
// Antarmuka umum
// ---------------------------------------------------------------------------

function classifierFactory(algorithm, types) {
    return (rows, features, target) =>
        algorithm === 'knn'
            ? fitKnn(rows, features, target, types)
            : fitNaiveBayes(rows, features, target, types);
}

/**
 * Latih model lalu evaluasi pada data uji.
 *
 * @returns {{ ok: true, model: {...} } | { ok: false, message: string }}
 */
export function trainModel({
    table,
    profile,
    target,
    features,
    algorithm,
    testRatio = 0.2,
    seed = 42,
}) {
    const types = Object.fromEntries(
        profile.columns.map((column) => [column.name, column.type]),
    );
    const targetType = types[target];

    if (!targetType) {
        return { ok: false, message: 'Kolom target tidak ditemukan.' };
    }

    if (!features.length) {
        return { ok: false, message: 'Pilih minimal satu kolom fitur.' };
    }

    const kind = isNumericType(targetType) ? 'regression' : 'classification';
    const chosen =
        algorithm && ALGORITHM_OPTIONS[kind].some((item) => item.value === algorithm)
            ? algorithm
            : ALGORITHM_OPTIONS[kind][0].value;

    // Regresi hanya menerima fitur numerik; kolom kategori butuh encoding yang
    // belum tersedia, jadi lebih baik dikeluarkan terang-terangan.
    const usableFeatures =
        kind === 'regression'
            ? features.filter((feature) => isNumericType(types[feature]))
            : features;

    if (!usableFeatures.length) {
        return {
            ok: false,
            message: 'Regresi membutuhkan minimal satu fitur numerik.',
        };
    }

    const rows = table.rows.filter((row) => usable(row, usableFeatures, target));

    if (rows.length < 20) {
        return {
            ok: false,
            message: 'Baris lengkap terlalu sedikit untuk dilatih (minimal 20).',
        };
    }

    const { train, test } = trainTestSplit(rows, testRatio, seed);

    if (kind === 'classification') {
        const fit = classifierFactory(chosen, types);
        const fitted = fit(train, usableFeatures, target);
        const actual = test.map((row) => row[target]);
        const predicted = test.map((row) => fitted.predict(row));
        const evaluation = classificationMetrics(actual, predicted, fitted.labels);

        // ROC hanya bermakna untuk dua kelas. Kelas positif diambil dari kelas
        // yang lebih jarang, karena itu yang biasanya ingin ditemukan.
        let roc = null;

        if (fitted.labels.length === 2) {
            const counts = fitted.labels.map(
                (label) => train.filter((row) => row[target] === label).length,
            );
            const positive = fitted.labels[counts[0] <= counts[1] ? 0 : 1];

            roc = rocCurve(
                actual,
                test.map((row) => fitted.probability(row, positive)),
                positive,
            );

            if (roc) {
                roc.positiveLabel = positive;
            }
        }

        return {
            ok: true,
            model: {
                kind,
                algorithm: ALGORITHM_LABEL[chosen],
                algorithmKey: chosen,
                target,
                features: usableFeatures,
                labels: fitted.labels,
                trainSize: train.length,
                testSize: test.length,
                evaluation,
                roc,
                predict: fitted.predict,
                featureImportance: featureImportance({
                    fit,
                    train,
                    test,
                    features: usableFeatures,
                    target,
                }),
                learningCurve: learningCurve({
                    fit,
                    train,
                    test,
                    features: usableFeatures,
                    target,
                }),
            },
        };
    }

    const alpha = chosen === 'ridge' ? rows.length * 0.05 : 0;
    const fitted = fitLinearRegression(train, usableFeatures, target, alpha);
    const actual = test.map((row) => Number(row[target]));
    const predicted = test.map((row) => fitted.predict(row));
    const evaluation = regressionMetrics(actual, predicted);

    // Koefisien dibakukan dengan simpangan baku fitur supaya kolom bersatuan
    // besar tidak otomatis terlihat paling berpengaruh.
    const weights = fitted.coefficients
        .map(({ feature, value }) => ({
            feature,
            weight: Math.abs(value * stdDev(rows.map((row) => Number(row[feature])))),
        }))
        .sort((a, b) => b.weight - a.weight);
    const total = weights.reduce((sum, item) => sum + item.weight, 0) || 1;

    return {
        ok: true,
        model: {
            kind,
            algorithm: ALGORITHM_LABEL[chosen],
            algorithmKey: chosen,
            target,
            features: usableFeatures,
            trainSize: train.length,
            testSize: test.length,
            evaluation,
            coefficients: fitted.coefficients,
            intercept: fitted.intercept,
            predict: fitted.predict,
            roc: null,
            scatter: actual.map((value, index) => ({
                x: value,
                y: Number(predicted[index].toFixed(2)),
            })),
            featureImportance: weights.map((item) => ({
                feature: item.feature,
                score: item.weight / total,
            })),
            learningCurve: null,
        },
    };
}

/*
 * Kontribusi fitur diukur dengan melatih ulang memakai satu fitur saja: makin
 * tinggi akurasinya, makin besar peran fitur tersebut. Cara ini berlaku untuk
 * algoritma klasifikasi mana pun, tidak bergantung pada bentuk parameternya.
 */
function featureImportance({ fit, train, test, features, target }) {
    const actual = test.map((row) => row[target]);

    const scores = features.map((feature) => {
        const fitted = fit(train, [feature], target);
        const predicted = test.map((row) => fitted.predict(row));
        const correct = predicted.filter((label, index) => label === actual[index]).length;

        return { feature, score: correct / (test.length || 1) };
    });

    const total = scores.reduce((sum, item) => sum + item.score, 0) || 1;

    return scores
        .map((item) => ({ feature: item.feature, score: item.score / total }))
        .sort((a, b) => b.score - a.score);
}

/*
 * Learning curve: akurasi diukur pada porsi data latih yang makin besar. Jarak
 * yang melebar antara kurva latih dan validasi menandakan model mulai menghafal.
 */
function learningCurve({ fit, train, test, features, target }) {
    const fractions = [0.2, 0.4, 0.6, 0.8, 1];
    const actualTest = test.map((row) => row[target]);

    const accuracy = (fitted, rows, actual) => {
        const predicted = rows.map((row) => fitted.predict(row));
        const correct = predicted.filter((label, index) => label === actual[index]).length;

        return Number((correct / (rows.length || 1)).toFixed(4));
    };

    const trainScores = [];
    const testScores = [];

    for (const fraction of fractions) {
        const size = Math.max(5, Math.round(train.length * fraction));
        const subset = train.slice(0, size);
        const fitted = fit(subset, features, target);

        trainScores.push(accuracy(fitted, subset, subset.map((row) => row[target])));
        testScores.push(accuracy(fitted, test, actualTest));
    }

    return {
        labels: fractions.map((fraction) => `${Math.round(fraction * 100)}%`),
        series: [
            { label: 'Akurasi latih', data: trainScores },
            { label: 'Akurasi validasi', data: testScores },
        ],
    };
}
