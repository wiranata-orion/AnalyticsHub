/*
 * Metrik evaluasi model.
 *
 * Dipakai halaman Machine Learning (evaluasi model) dan Data Mining (ringkasan
 * hasil klasifikasi/regresi). Semua metrik dihitung dari prediksi pada data uji,
 * bukan data latih — angka pada data latih selalu terlalu optimistis.
 */

export function confusionMatrix(actual, predicted, labels) {
    const index = new Map(labels.map((label, position) => [label, position]));
    const matrix = labels.map(() => labels.map(() => 0));

    for (let row = 0; row < actual.length; row += 1) {
        const actualIndex = index.get(actual[row]);
        const predictedIndex = index.get(predicted[row]);

        if (actualIndex !== undefined && predictedIndex !== undefined) {
            matrix[actualIndex][predictedIndex] += 1;
        }
    }

    return matrix;
}

/**
 * Presisi/recall/F1 dirata-ratakan makro: tiap kelas berbobot sama, sehingga
 * kelas minoritas tidak tertutup oleh kelas mayoritas.
 */
export function classificationMetrics(actual, predicted, labels) {
    const matrix = confusionMatrix(actual, predicted, labels);
    const total = actual.length || 1;
    const correct = labels.reduce(
        (sum, _, position) => sum + matrix[position][position],
        0,
    );

    const perClass = labels.map((label, position) => {
        const truePositive = matrix[position][position];
        const predictedPositive = labels.reduce(
            (sum, __, row) => sum + matrix[row][position],
            0,
        );
        const actualPositive = matrix[position].reduce(
            (sum, value) => sum + value,
            0,
        );

        const precision = predictedPositive ? truePositive / predictedPositive : 0;
        const recall = actualPositive ? truePositive / actualPositive : 0;
        const f1 =
            precision + recall ? (2 * precision * recall) / (precision + recall) : 0;

        return { label, precision, recall, f1, support: actualPositive };
    });

    const average = (key) =>
        perClass.reduce((sum, item) => sum + item[key], 0) / (perClass.length || 1);

    return {
        labels,
        matrix,
        perClass,
        accuracy: correct / total,
        precision: average('precision'),
        recall: average('recall'),
        f1: average('f1'),
    };
}

/**
 * Kurva ROC untuk kasus dua kelas: ambang digeser dari tinggi ke rendah dan tiap
 * titik mencatat pasangan (false positive rate, true positive rate).
 */
export function rocCurve(actual, scores, positiveLabel) {
    const pairs = actual
        .map((label, index) => ({ label, score: scores[index] }))
        .sort((a, b) => b.score - a.score);

    const positives = pairs.filter((pair) => pair.label === positiveLabel).length;
    const negatives = pairs.length - positives;

    if (!positives || !negatives) {
        return null;
    }

    const points = [{ x: 0, y: 0 }];
    let truePositive = 0;
    let falsePositive = 0;
    let auc = 0;
    let previousX = 0;

    for (const pair of pairs) {
        if (pair.label === positiveLabel) {
            truePositive += 1;
        } else {
            falsePositive += 1;
        }

        const x = falsePositive / negatives;
        const y = truePositive / positives;

        // Luas di bawah kurva dijumlahkan per trapesium saat FPR bertambah.
        if (x > previousX) {
            auc += (x - previousX) * y;
            previousX = x;
        }

        points.push({ x: Number(x.toFixed(4)), y: Number(y.toFixed(4)) });
    }

    return { points, auc };
}

export function regressionMetrics(actual, predicted) {
    const count = actual.length || 1;
    const average = actual.reduce((sum, value) => sum + value, 0) / count;

    let residual = 0;
    let totalVariance = 0;
    let absolute = 0;

    for (let index = 0; index < actual.length; index += 1) {
        const error = actual[index] - predicted[index];

        residual += error * error;
        absolute += Math.abs(error);
        totalVariance += (actual[index] - average) ** 2;
    }

    return {
        r2: totalVariance ? 1 - residual / totalVariance : 0,
        rmse: Math.sqrt(residual / count),
        mae: absolute / count,
    };
}

export const asPercent = (value) =>
    `${(value * 100).toFixed(1).replace('.', ',')}%`;

export const asDecimal = (value, digits = 3) =>
    Number.isFinite(value) ? value.toFixed(digits).replace('.', ',') : '—';
