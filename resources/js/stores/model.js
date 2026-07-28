import { computed, markRaw, ref } from 'vue';
import { defineStore } from 'pinia';
import { datasetAnalysis } from '@/Utils/analysis';
import { trainModel } from '@/Utils/ml/supervised';
import { asDecimal, asPercent } from '@/Utils/ml/metrics';
import { isNumericType } from '@/Utils/profiler';
import { datasets as placeholderDatasets } from '@/data/placeholder';

/*
 * Model yang sudah dilatih, dibagikan lintas halaman.
 *
 * "Saved Models" berarti model tetap ada setelah berpindah menu, sehingga bisa
 * dievaluasi ulang atau dipakai memprediksi dataset lain tanpa training ulang.
 * Objek engine (fungsi predict, hasil evaluasi) disimpan `markRaw` karena hanya
 * dibaca apa adanya — memproksikannya ke sistem reaktif tidak ada gunanya dan
 * membuat setiap akses lebih mahal.
 *
 * Saat backend siap, `train()` menjadi `POST /api/models` dan `predict()`
 * menjadi `POST /api/models/{id}/predict`; bentuk datanya sudah disamakan.
 */
let nextId = 1;

function summarize(engine) {
    return engine.kind === 'classification'
        ? { metric: 'Akurasi', score: asPercent(engine.evaluation.accuracy) }
        : { metric: 'R²', score: asDecimal(engine.evaluation.r2) };
}

function today() {
    return new Date().toLocaleDateString('id-ID', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
    });
}

export const useModelStore = defineStore('model', () => {
    const items = ref([]);
    const selectedId = ref(null);
    // Hasil prediksi terakhir ikut disimpan di store supaya tetap terlihat
    // setelah pengguna berpindah menu dan kembali ke halaman ini.
    const lastPrediction = ref(null);
    let hasSeeded = false;

    const selected = computed(
        () => items.value.find((item) => item.id === selectedId.value) ?? null,
    );

    function datasetName(id) {
        return (
            placeholderDatasets.find((dataset) => dataset.id === Number(id))?.name ??
            `dataset #${id}`
        );
    }

    /**
     * Latih model baru pada dataset terpilih.
     *
     * @returns {{ ok: true, model } | { ok: false, message }}
     */
    function train({ datasetId, target, features, name, algorithm }) {
        const { table, profile } = datasetAnalysis(datasetId);
        const result = trainModel({ table, profile, target, features, algorithm });

        if (!result.ok) {
            return result;
        }

        const engine = result.model;
        const model = {
            id: nextId++,
            name: name?.trim() || `${engine.kind === 'classification' ? 'Klasifikasi' : 'Regresi'} ${target}`,
            datasetId: Number(datasetId),
            datasetName: datasetName(datasetId),
            algorithm: engine.algorithm,
            kind: engine.kind,
            target,
            features: engine.features,
            status: 'ready',
            trained_at: today(),
            ...summarize(engine),
            engine: markRaw(engine),
        };

        items.value = [model, ...items.value];
        selectedId.value = model.id;

        return { ok: true, model };
    }

    function remove(id) {
        items.value = items.value.filter((item) => item.id !== Number(id));

        if (selectedId.value === Number(id)) {
            selectedId.value = items.value[0]?.id ?? null;
        }

        // Hasil prediksi milik model yang dihapus tidak boleh tertinggal di
        // layar seolah masih berlaku.
        if (lastPrediction.value?.modelId === Number(id)) {
            lastPrediction.value = null;
        }
    }

    function select(id) {
        selectedId.value = Number(id);
    }

    /**
     * Jalankan model pada dataset lain. Dataset tujuan wajib memuat seluruh
     * kolom fitur model — tanpa itu prediksinya tidak bisa dipertanggungjawabkan,
     * jadi kolom yang hilang dilaporkan alih-alih diisi nilai default diam-diam.
     */
    function predict(modelId, datasetId) {
        const model = items.value.find((item) => item.id === Number(modelId));

        if (!model) {
            return { ok: false, message: 'Model tidak ditemukan.' };
        }

        const { table } = datasetAnalysis(datasetId);
        const available = new Set(table.columns.map((column) => column.name));
        const missing = model.features.filter((feature) => !available.has(feature));

        if (missing.length) {
            return {
                ok: false,
                message: `Dataset ini tidak memiliki kolom ${missing
                    .map((feature) => `"${feature}"`)
                    .join(', ')} yang dipakai model.`,
            };
        }

        const usable = table.rows.filter((row) =>
            model.features.every(
                (feature) => row[feature] !== null && row[feature] !== undefined,
            ),
        );

        if (!usable.length) {
            return {
                ok: false,
                message: 'Tidak ada baris dengan seluruh kolom fitur terisi.',
            };
        }

        const predictions = usable.map((row) => model.engine.predict(row));

        const finish = (result) => {
            lastPrediction.value = {
                ...result,
                modelId: model.id,
                modelName: model.name,
                datasetId: Number(datasetId),
            };

            return lastPrediction.value;
        };

        if (model.kind === 'classification') {
            const tally = new Map();

            for (const label of predictions) {
                tally.set(label, (tally.get(label) ?? 0) + 1);
            }

            const distribution = [...tally.entries()]
                .map(([label, count]) => ({
                    label,
                    count,
                    share: (count / predictions.length) * 100,
                }))
                .sort((a, b) => b.count - a.count);

            return finish({
                ok: true,
                kind: 'classification',
                datasetName: datasetName(datasetId),
                total: predictions.length,
                skipped: table.rows.length - usable.length,
                distribution,
                sample: usable.slice(0, 8).map((row, index) => ({
                    id: index + 1,
                    features: model.features
                        .map((feature) => `${feature}: ${row[feature]}`)
                        .join(' · '),
                    prediction: predictions[index],
                })),
            });
        }

        const numbers = predictions.filter(Number.isFinite);
        const average = numbers.reduce((sum, value) => sum + value, 0) / (numbers.length || 1);

        return finish({
            ok: true,
            kind: 'regression',
            datasetName: datasetName(datasetId),
            total: numbers.length,
            skipped: table.rows.length - usable.length,
            average,
            min: Math.min(...numbers),
            max: Math.max(...numbers),
            sample: usable.slice(0, 8).map((row, index) => ({
                id: index + 1,
                features: model.features
                    .map((feature) => `${feature}: ${row[feature]}`)
                    .join(' · '),
                prediction: Number(predictions[index].toFixed(2)).toLocaleString('id-ID'),
            })),
        });
    }

    /*
     * Halaman Machine Learning tidak seharusnya kosong saat pertama dibuka.
     * Alih-alih menaruh angka mati, dua model contoh benar-benar dilatih dari
     * dataset yang tersedia — evaluasinya jadi konsisten dengan datanya.
     *
     * Penanda `hasSeeded` terpisah dari jumlah model: kalau hanya mengecek
     * daftar kosong, model contoh akan muncul kembali setiap kali halaman
     * dikunjungi ulang setelah pengguna menghapus semuanya.
     */
    function seed() {
        if (hasSeeded || items.value.length) {
            return;
        }

        hasSeeded = true;

        for (const preset of [
            { datasetId: 2, target: 'churn', name: 'Prediksi Churn Pelanggan' },
            { datasetId: 1, target: 'pendapatan', name: 'Estimasi Pendapatan' },
        ]) {
            const { profile } = datasetAnalysis(preset.datasetId);
            const features = profile.columns
                .filter(
                    (column) =>
                        !column.isIdentifier &&
                        column.name !== preset.target &&
                        column.type !== 'datetime' &&
                        // Baris dengan fitur kosong tidak bisa dilatih maupun
                        // diprediksi, jadi kolom yang banyak kosongnya tidak
                        // dipilih secara default — memakainya akan membuang
                        // seperlima dataset tanpa pemberitahuan.
                        column.missing < 15 &&
                        (isNumericType(column.type) || column.unique <= 8),
                )
                .map((column) => column.name);

            train({ ...preset, features });
        }

        // Model pertama dalam daftar tetap yang paling relevan untuk dibuka.
        selectedId.value = items.value[items.value.length - 1]?.id ?? null;
    }

    return {
        items,
        selectedId,
        selected,
        lastPrediction,
        train,
        remove,
        select,
        predict,
        seed,
    };
});
