<script setup>
import { computed, ref, watch } from 'vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import StatusBadge from '@/Components/UI/StatusBadge.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useModelStore } from '@/stores/model';
import { useToastStore } from '@/stores/toast';
import { useConfirmStore } from '@/stores/confirm';
import { datasetAnalysis } from '@/Utils/analysis';
import { ALGORITHM_OPTIONS } from '@/Utils/ml/supervised';
import { asDecimal, asPercent } from '@/Utils/ml/metrics';
import { isNumericType } from '@/Utils/profiler';
import { sequentialAt } from '@/Utils/palette';

/*
 * Halaman ini menutup satu siklus penuh:
 *
 *   Train Model  -> pilih target, fitur, dan algoritma, lalu latih.
 *   Evaluation   -> metrik dihitung dari data uji yang dipisahkan saat training.
 *   Prediction   -> model dipakai pada dataset lain.
 *   Saved Models -> hasil training tersimpan di store, jadi berpindah menu tidak
 *                   menghapusnya dan model bisa dipakai lagi tanpa training ulang.
 *
 * Dataset untuk training diambil dari pemilih di header; dataset untuk prediksi
 * dipilih terpisah, karena justru bedanya yang jadi inti fitur prediksi.
 */
const datasetStore = useDatasetStore();
const modelStore = useModelStore();
const toast = useToastStore();
const confirm = useConfirmStore();

modelStore.seed();

const analysis = computed(() => datasetAnalysis(datasetStore.selectedId));
const profile = computed(() => analysis.value.profile);

// --- Train Model ------------------------------------------------------------

const trainerOpen = ref(false);

const targetOptions = computed(() =>
    profile.value.columns.filter(
        (column) =>
            !column.isIdentifier &&
            column.type !== 'datetime' &&
            (isNumericType(column.type) || column.unique <= 12),
    ),
);

const form = ref({ name: '', target: '', features: [], algorithm: '' });

const targetMeta = computed(() =>
    profile.value.columns.find((column) => column.name === form.value.target),
);

const modelKind = computed(() =>
    targetMeta.value && isNumericType(targetMeta.value.type)
        ? 'regression'
        : 'classification',
);

const algorithmOptions = computed(() => ALGORITHM_OPTIONS[modelKind.value]);

const featureOptions = computed(() =>
    profile.value.columns.filter(
        (column) =>
            !column.isIdentifier &&
            column.name !== form.value.target &&
            column.type !== 'datetime' &&
            // Regresi belum menangani encoding kategori, jadi kolom kategori
            // tidak ditawarkan agar pilihan tidak diam-diam diabaikan.
            (modelKind.value === 'regression'
                ? isNumericType(column.type)
                : isNumericType(column.type) || column.unique <= 12),
    ),
);

/*
 * Kolom yang banyak kosongnya tetap ditawarkan, tetapi tidak dicentang di awal:
 * baris dengan fitur kosong ikut terbuang saat training, jadi memilihnya berarti
 * mengorbankan sebagian dataset — itu keputusan yang sebaiknya disengaja.
 */
const defaultFeatures = () =>
    featureOptions.value
        .filter((column) => column.missing < 15)
        .map((column) => column.name);

function resetForm() {
    const target = targetOptions.value[0]?.name ?? '';

    form.value = { name: '', target, features: [], algorithm: '' };
    form.value.features = defaultFeatures();
    form.value.algorithm = algorithmOptions.value[0].value;
}

resetForm();

watch(() => datasetStore.selectedId, resetForm);

// Berganti target mengubah jenis model, sehingga daftar fitur dan algoritma
// yang berlaku ikut berubah.
watch(
    () => form.value.target,
    () => {
        form.value.features = defaultFeatures();
        form.value.algorithm = algorithmOptions.value[0].value;
    },
);

function toggleFeature(name) {
    form.value.features = form.value.features.includes(name)
        ? form.value.features.filter((item) => item !== name)
        : [...form.value.features, name];
}

function submitTraining() {
    const result = modelStore.train({
        datasetId: datasetStore.selectedId,
        target: form.value.target,
        features: form.value.features,
        algorithm: form.value.algorithm,
        name: form.value.name,
    });

    if (!result.ok) {
        toast.push(result.message, 'warning');

        return;
    }

    trainerOpen.value = false;
    toast.push(
        `Model "${result.model.name}" selesai dilatih — ${result.model.metric} ${result.model.score}.`,
    );
}

// --- Saved Models -----------------------------------------------------------

// Kolom teks panjang dibungkus dan metrik digabung ke skor, supaya tabel muat
// tanpa harus digulir ke samping.
const MODEL_COLUMNS = [
    { key: 'name', label: 'Nama Model', wrap: true },
    { key: 'algorithm', label: 'Algoritma', wrap: true },
    { key: 'datasetName', label: 'Dataset', wrap: true },
    { key: 'target', label: 'Target', wrap: true },
    { key: 'score', label: 'Skor', align: 'right' },
    { key: 'status', label: 'Status' },
    { key: 'trained_at', label: 'Dilatih', align: 'right', wrap: true },
    { key: 'actions', label: '', align: 'right', width: '1%' },
];

async function removeModel(model) {
    const confirmed = await confirm.open({
        title: 'Hapus model',
        message: `Model "${model.name}" akan dihapus dan tidak bisa dipakai untuk prediksi lagi.`,
    });

    if (!confirmed) {
        return;
    }

    modelStore.remove(model.id);
    toast.push(`Model "${model.name}" dihapus.`);
}

// --- Model Evaluation -------------------------------------------------------

const selected = computed(() => modelStore.selected);
const engine = computed(() => selected.value?.engine ?? null);

const importanceChart = computed(() => {
    if (!engine.value?.featureImportance?.length) {
        return null;
    }

    const items = [...engine.value.featureImportance].slice(0, 8);

    return {
        labels: items.map((item) => item.feature),
        series: [
            {
                label: 'Kontribusi',
                data: items.map((item) => Number(item.score.toFixed(3))),
            },
        ],
    };
});

const rocChart = computed(() => {
    if (!engine.value?.roc) {
        return null;
    }

    return {
        auc: engine.value.roc.auc,
        positiveLabel: engine.value.roc.positiveLabel,
        series: [
            { label: 'Model', data: engine.value.roc.points },
            {
                // Garis acuan: model yang menebak acak berada di diagonal ini.
                label: 'Tebakan acak',
                data: [
                    { x: 0, y: 0 },
                    { x: 1, y: 1 },
                ],
            },
        ],
    };
});

/*
 * Confusion matrix memakai skala SEKUENSIAL satu rona: nilainya adalah jumlah
 * (besaran tanpa polaritas), bukan selisih dua arah. Angka tetap dicetak di
 * setiap sel, jadi warna hanya membantu memindai.
 */
const matrixCells = computed(() => {
    if (!engine.value || engine.value.kind !== 'classification') {
        return null;
    }

    const matrix = engine.value.evaluation.matrix;
    const highest = Math.max(...matrix.flat(), 1);

    return matrix.map((row) =>
        row.map((value) => {
            const ratio = value / highest;

            return {
                value,
                background: sequentialAt(ratio),
                color: ratio > 0.55 ? '#ffffff' : '#0b0b0b',
            };
        }),
    );
});

const evaluationRows = computed(() => {
    if (!engine.value) {
        return [];
    }

    const shared = [
        { label: 'Data Latih', value: `${engine.value.trainSize} baris` },
        { label: 'Data Uji', value: `${engine.value.testSize} baris` },
        { label: 'Fitur', value: String(engine.value.features.length) },
    ];

    if (engine.value.kind === 'regression') {
        const { r2, rmse, mae } = engine.value.evaluation;

        return [
            { label: 'R²', value: asDecimal(r2) },
            { label: 'RMSE', value: rmse.toLocaleString('id-ID', { maximumFractionDigits: 0 }) },
            { label: 'MAE', value: mae.toLocaleString('id-ID', { maximumFractionDigits: 0 }) },
            ...shared,
        ];
    }

    const { accuracy, precision, recall, f1 } = engine.value.evaluation;

    return [
        { label: 'Akurasi', value: asPercent(accuracy) },
        { label: 'Presisi', value: asPercent(precision) },
        { label: 'Recall', value: asPercent(recall) },
        { label: 'F1-Score', value: asPercent(f1) },
        ...(engine.value.roc
            ? [{ label: 'ROC-AUC', value: asDecimal(engine.value.roc.auc) }]
            : []),
        ...shared,
    ];
});

// --- Prediction -------------------------------------------------------------

/*
 * Pilihan formulir prediksi boleh hilang saat berpindah halaman, tetapi HASIL
 * prediksinya tidak — itu pekerjaan yang sudah dijalankan pengguna, jadi
 * disimpan di store dan ditampilkan lagi saat kembali ke halaman ini.
 */
const prediction = ref({ modelId: null, datasetId: null });
const predictionResult = computed(() => modelStore.lastPrediction);

watch(
    () => modelStore.items.length,
    () => {
        if (!modelStore.items.some((item) => item.id === prediction.value.modelId)) {
            prediction.value = {
                modelId: modelStore.lastPrediction?.modelId ?? modelStore.items[0]?.id ?? null,
                datasetId:
                    prediction.value.datasetId ??
                    modelStore.lastPrediction?.datasetId ??
                    datasetStore.items[0]?.id ??
                    null,
            };
        }
    },
    { immediate: true },
);

const PREDICTION_COLUMNS = [
    { key: 'features', label: 'Nilai Fitur', wrap: true },
    { key: 'prediction', label: 'Prediksi', align: 'right' },
];

function runPrediction() {
    if (!prediction.value.modelId || !prediction.value.datasetId) {
        toast.push('Pilih model dan dataset tujuan terlebih dahulu.', 'warning');

        return;
    }

    const result = modelStore.predict(
        prediction.value.modelId,
        prediction.value.datasetId,
    );

    if (!result.ok) {
        toast.push(result.message, 'warning');

        return;
    }

    toast.push(`${result.total} baris diprediksi dari ${result.datasetName}.`);
}
</script>

<template>
    <PageHeader
        title="Machine Learning"
        description="Latih model dari dataset yang sudah dibersihkan, tinjau evaluasinya, lalu pakai untuk memprediksi dataset lain."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Machine Learning' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
            <AppButton
                variant="primary"
                :icon="trainerOpen ? 'close' : 'plus'"
                @click="trainerOpen = !trainerOpen"
            >
                {{ trainerOpen ? 'Tutup Formulir' : 'Latih Model' }}
            </AppButton>
        </template>
    </PageHeader>

    <!-- Train Model -->
    <AppCard
        v-if="trainerOpen"
        class="mb-4"
        title="Latih Model Baru"
        :subtitle="`Dataset: ${datasetStore.selected?.name ?? '—'} · ${profile.rowCount.toLocaleString('id-ID')} baris`"
    >
        <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div>
                <label
                    for="model-name"
                    class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark"
                >
                    Nama Model (opsional)
                </label>
                <input
                    id="model-name"
                    v-model="form.name"
                    type="text"
                    placeholder="Mengikuti target yang dipilih"
                    class="focus-ring h-9 w-full rounded-lg border-hairline bg-plane px-3 text-sm text-ink placeholder:text-ink-3 focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                />
            </div>

            <div>
                <label
                    for="model-target"
                    class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark"
                >
                    Target
                </label>
                <select
                    id="model-target"
                    v-model="form.target"
                    class="focus-ring h-9 w-full rounded-lg border-hairline bg-plane py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                >
                    <option
                        v-for="column in targetOptions"
                        :key="column.name"
                        :value="column.name"
                    >
                        {{ column.name }} ({{ column.type }})
                    </option>
                </select>
            </div>

            <div>
                <label
                    for="model-algorithm"
                    class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark"
                >
                    Algoritma
                </label>
                <select
                    id="model-algorithm"
                    v-model="form.algorithm"
                    class="focus-ring h-9 w-full rounded-lg border-hairline bg-plane py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                >
                    <option
                        v-for="option in algorithmOptions"
                        :key="option.value"
                        :value="option.value"
                    >
                        {{ option.label }}
                    </option>
                </select>
            </div>
        </div>

        <div class="mt-4">
            <p class="mb-2 text-xs font-medium text-ink-2 dark:text-ink-2-dark">
                Fitur ({{ form.features.length }} dari {{ featureOptions.length }} dipilih)
            </p>

            <div class="flex flex-wrap gap-2">
                <button
                    v-for="column in featureOptions"
                    :key="column.name"
                    type="button"
                    class="focus-ring rounded-lg px-3 py-1.5 text-xs font-medium ring-1 ring-inset transition-colors"
                    :class="
                        form.features.includes(column.name)
                            ? 'bg-accent text-white ring-accent dark:bg-accent-dark dark:ring-accent-dark'
                            : 'text-ink-2 ring-hairline hover:bg-plane dark:text-ink-2-dark dark:ring-hairline-dark dark:hover:bg-raised-dark'
                    "
                    :aria-pressed="form.features.includes(column.name)"
                    @click="toggleFeature(column.name)"
                >
                    {{ column.name }}
                </button>
            </div>
        </div>

        <template #footer>
            <div class="flex flex-wrap items-center justify-between gap-3">
                <p class="text-xs text-ink-3">
                    {{
                        modelKind === 'regression'
                            ? 'Target numerik — model regresi, dievaluasi dengan R², RMSE, dan MAE.'
                            : 'Target kategorikal — model klasifikasi, dievaluasi dengan akurasi, presisi, recall, dan F1.'
                    }}
                    20% data disisihkan sebagai data uji.
                </p>
                <AppButton variant="primary" icon="play" @click="submitTraining">
                    Latih Model
                </AppButton>
            </div>
        </template>
    </AppCard>

    <!-- Saved Models -->
    <AppCard
        title="Model Tersimpan"
        subtitle="Model tetap tersimpan saat berpindah menu dan bisa dipakai ulang tanpa training ulang."
        flush
    >
        <DataTable
            v-if="modelStore.items.length"
            :columns="MODEL_COLUMNS"
            :rows="modelStore.items"
        >
            <template #cell-name="{ row }">
                <span class="flex items-center gap-2">
                    <span class="font-medium text-ink dark:text-ink-dark">
                        {{ row.name }}
                    </span>
                    <AppBadge v-if="row.id === modelStore.selectedId" variant="info">
                        Ditampilkan
                    </AppBadge>
                </span>
            </template>

            <template #cell-score="{ row }">
                <span class="whitespace-nowrap">
                    <span class="text-ink-3">{{ row.metric }}</span>
                    <span class="ml-1 font-medium tabular-nums text-ink dark:text-ink-dark">
                        {{ row.score }}
                    </span>
                </span>
            </template>

            <template #cell-status="{ row }">
                <StatusBadge :status="row.status" />
            </template>

            <template #cell-actions="{ row }">
                <div class="flex items-center justify-end gap-1">
                    <button
                        type="button"
                        class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-ink dark:hover:text-ink-dark"
                        title="Tampilkan evaluasi"
                        @click="modelStore.select(row.id)"
                    >
                        <AppIcon name="eye" class="h-4 w-4" />
                        <span class="sr-only">Tampilkan evaluasi {{ row.name }}</span>
                    </button>
                    <button
                        type="button"
                        class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-status-critical"
                        title="Hapus model"
                        @click="removeModel(row)"
                    >
                        <AppIcon name="trash" class="h-4 w-4" />
                        <span class="sr-only">Hapus {{ row.name }}</span>
                    </button>
                </div>
            </template>
        </DataTable>

        <EmptyState
            v-else
            icon="ml"
            title="Belum ada model"
            description="Gunakan tombol Latih Model untuk memilih target, fitur, dan algoritma, lalu melatih model pertama."
        >
            <template #action>
                <AppButton variant="primary" icon="plus" @click="trainerOpen = true">
                    Latih Model
                </AppButton>
            </template>
        </EmptyState>
    </AppCard>

    <!-- Model Evaluation -->
    <template v-if="selected">
        <div class="mb-3 mt-6 flex flex-wrap items-baseline justify-between gap-2">
            <h2 class="text-sm font-semibold text-ink dark:text-ink-dark">
                Evaluasi Model
            </h2>
            <p class="text-xs text-ink-3">
                {{ selected.name }} · {{ selected.algorithm }} · target
                {{ selected.target }}
            </p>
        </div>

        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChartPanel
                v-if="importanceChart"
                title="Feature Importance"
                :subtitle="
                    selected.kind === 'classification'
                        ? 'Akurasi saat model dilatih dengan satu fitur saja'
                        : 'Besar koefisien setelah dibakukan dengan simpangan baku fitur'
                "
                type="bar"
                horizontal
                :labels="importanceChart.labels"
                :series="importanceChart.series"
                :height="280"
            />

            <ChartPanel
                v-if="engine.learningCurve"
                title="Learning Curve"
                subtitle="Akurasi terhadap proporsi data latih"
                type="line"
                :labels="engine.learningCurve.labels"
                :series="engine.learningCurve.series"
                :height="280"
            />

            <ChartPanel
                v-else-if="engine.scatter"
                title="Prediksi vs Aktual"
                subtitle="Titik ideal berada di garis diagonal"
                type="scatter"
                :series="[{ label: 'Baris data uji', data: engine.scatter }]"
                :height="280"
            />
        </div>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <AppCard
                v-if="matrixCells"
                title="Confusion Matrix"
                subtitle="Prediksi model pada data uji"
            >
                <!-- Lebar kolom dibagi rata lewat `table-fixed` supaya
                     matriks selalu muat di dalam kartunya, berapa pun jumlah
                     kelasnya, dan tidak perlu digulir ke samping. -->
                <table
                    class="w-full table-fixed border-separate border-spacing-1 text-sm"
                >
                    <colgroup>
                        <col style="width: 26%" />
                        <col v-for="label in engine.labels" :key="label" />
                    </colgroup>
                    <thead>
                        <tr>
                            <th class="p-1" />
                            <th
                                :colspan="engine.labels.length"
                                class="pb-1 text-center text-xs font-medium text-ink-3"
                            >
                                Prediksi
                            </th>
                        </tr>
                        <tr>
                            <th class="p-1" />
                            <th
                                v-for="label in engine.labels"
                                :key="label"
                                class="truncate px-1 pb-1 text-center text-xs font-medium text-ink-2 dark:text-ink-2-dark"
                                :title="label"
                            >
                                {{ label }}
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, rowIndex) in matrixCells" :key="rowIndex">
                            <th
                                class="truncate pr-2 text-right text-xs font-medium text-ink-2 dark:text-ink-2-dark"
                                :title="engine.labels[rowIndex]"
                            >
                                {{ engine.labels[rowIndex] }}
                            </th>
                            <td
                                v-for="(cell, colIndex) in row"
                                :key="colIndex"
                                class="h-14 rounded-lg text-center font-medium tabular-nums"
                                :style="{
                                    backgroundColor: cell.background,
                                    color: cell.color,
                                }"
                            >
                                {{ cell.value.toLocaleString('id-ID') }}
                            </td>
                        </tr>
                    </tbody>
                </table>

                <p class="mt-3 text-xs text-ink-3">
                    Diagonal utama adalah prediksi benar. Baris = kelas sebenarnya.
                </p>
            </AppCard>

            <div :class="matrixCells ? 'lg:col-span-2' : 'lg:col-span-3'">
                <AppCard title="Ringkasan Evaluasi">
                    <div class="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-4">
                        <div v-for="metric in evaluationRows" :key="metric.label">
                            <p
                                class="text-xs font-medium uppercase tracking-wide text-ink-3"
                            >
                                {{ metric.label }}
                            </p>
                            <p
                                class="mt-1.5 text-xl font-semibold text-ink dark:text-ink-dark"
                            >
                                {{ metric.value }}
                            </p>
                        </div>
                    </div>

                    <template #footer>
                        <div class="flex items-start gap-2">
                            <AppIcon
                                :name="
                                    selected.kind === 'classification'
                                        ? engine.evaluation.accuracy >= 0.85
                                            ? 'check'
                                            : 'warning'
                                        : engine.evaluation.r2 >= 0.7
                                          ? 'check'
                                          : 'warning'
                                "
                                class="mt-0.5 h-4 w-4 shrink-0"
                                :class="
                                    (
                                        selected.kind === 'classification'
                                            ? engine.evaluation.accuracy >= 0.85
                                            : engine.evaluation.r2 >= 0.7
                                    )
                                        ? 'text-[#006300] dark:text-status-good'
                                        : 'text-[#8a5a00] dark:text-status-warning'
                                "
                            />
                            <p class="text-xs text-ink-2 dark:text-ink-2-dark">
                                Fitur yang dipakai: {{ engine.features.join(', ') }}.
                                Seluruh metrik dihitung dari
                                {{ engine.testSize }} baris uji yang tidak ikut dilatih.
                            </p>
                        </div>
                    </template>
                </AppCard>
            </div>
        </div>

        <ChartPanel
            v-if="rocChart"
            class="mt-4"
            title="ROC Curve"
            :subtitle="`Kelas positif: ${rocChart.positiveLabel} · AUC ${asDecimal(rocChart.auc)} — makin jauh di atas garis acuan, makin baik`"
            type="scatter"
            :series="rocChart.series"
            :height="300"
        />
    </template>

    <!-- Prediction -->
    <div class="mb-3 mt-6 flex flex-wrap items-baseline justify-between gap-2">
        <h2 class="text-sm font-semibold text-ink dark:text-ink-dark">
            Prediksi
        </h2>
        <p class="text-xs text-ink-3">
            Jalankan model tersimpan pada dataset lain
        </p>
    </div>

    <AppCard
        title="Prediksi Dataset Baru"
        subtitle="Dataset tujuan harus memuat seluruh kolom fitur yang dipakai model."
    >
        <div class="grid grid-cols-1 items-end gap-4 sm:grid-cols-3">
            <div>
                <label
                    for="predict-model"
                    class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark"
                >
                    Model
                </label>
                <select
                    id="predict-model"
                    v-model="prediction.modelId"
                    class="focus-ring h-9 w-full rounded-lg border-hairline bg-plane py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                >
                    <option
                        v-for="model in modelStore.items"
                        :key="model.id"
                        :value="model.id"
                    >
                        {{ model.name }} ({{ model.target }})
                    </option>
                </select>
            </div>

            <div>
                <label
                    for="predict-dataset"
                    class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark"
                >
                    Dataset Tujuan
                </label>
                <select
                    id="predict-dataset"
                    v-model="prediction.datasetId"
                    class="focus-ring h-9 w-full rounded-lg border-hairline bg-plane py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                >
                    <option
                        v-for="dataset in datasetStore.items"
                        :key="dataset.id"
                        :value="dataset.id"
                    >
                        {{ dataset.name }}
                    </option>
                </select>
            </div>

            <AppButton
                variant="primary"
                icon="play"
                :disabled="!modelStore.items.length"
                @click="runPrediction"
            >
                Jalankan Prediksi
            </AppButton>
        </div>

        <template v-if="predictionResult" #footer>
            <div class="space-y-4">
                <p class="text-xs text-ink-2 dark:text-ink-2-dark">
                    {{ predictionResult.total.toLocaleString('id-ID') }} baris
                    diprediksi oleh "{{ predictionResult.modelName }}" dari
                    {{ predictionResult.datasetName }}.
                    <template v-if="predictionResult.skipped">
                        {{ predictionResult.skipped }} baris dilewati karena ada
                        kolom fitur yang kosong.
                    </template>
                </p>

                <div
                    v-if="predictionResult.kind === 'classification'"
                    class="flex flex-wrap gap-2"
                >
                    <AppBadge
                        v-for="item in predictionResult.distribution"
                        :key="item.label"
                    >
                        {{ item.label }}: {{ item.count }} ({{
                            item.share.toFixed(1).replace('.', ',')
                        }}%)
                    </AppBadge>
                </div>

                <div v-else class="flex flex-wrap gap-2">
                    <AppBadge>
                        Rata-rata:
                        {{ predictionResult.average.toLocaleString('id-ID', { maximumFractionDigits: 0 }) }}
                    </AppBadge>
                    <AppBadge>
                        Minimum:
                        {{ predictionResult.min.toLocaleString('id-ID', { maximumFractionDigits: 0 }) }}
                    </AppBadge>
                    <AppBadge>
                        Maksimum:
                        {{ predictionResult.max.toLocaleString('id-ID', { maximumFractionDigits: 0 }) }}
                    </AppBadge>
                </div>

                <div
                    class="overflow-hidden rounded-lg border border-hairline dark:border-hairline-dark"
                >
                    <DataTable
                        :columns="PREDICTION_COLUMNS"
                        :rows="predictionResult.sample"
                    >
                        <template #cell-prediction="{ row }">
                            <span class="font-medium text-ink dark:text-ink-dark">
                                {{ row.prediction }}
                            </span>
                        </template>
                    </DataTable>
                </div>
            </div>
        </template>
    </AppCard>
</template>
