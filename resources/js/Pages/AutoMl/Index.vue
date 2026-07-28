<script setup>
import { computed, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useToastStore } from '@/stores/toast';
import { api } from '@/Utils/api';
import { asDecimal, asPercent } from '@/Utils/ml/metrics';

/*
 * AutoML: satu klik mencoba tujuh algoritma pada pembagian data yang sama,
 * membandingkannya, dan menandai pemenang. Setiap kandidat ikut tersimpan
 * sebagai model di Model Comparison; artefak pemenang disimpan untuk prediksi.
 */
const datasetStore = useDatasetStore();
const toast = useToastStore();
const { selectedId } = storeToRefs(datasetStore);

const ALGORITHMS = [
    { value: 'random_forest', label: 'Random Forest' },
    { value: 'decision_tree', label: 'Decision Tree' },
    { value: 'xgboost', label: 'XGBoost' },
    { value: 'knn', label: 'KNN' },
    { value: 'naive_bayes', label: 'Naive Bayes' },
    { value: 'svm', label: 'SVM' },
    { value: 'logistic_regression', label: 'Logistic Regression' },
];

const target = ref('');
const features = ref([]);
const algorithms = ref(ALGORITHMS.map((item) => item.value));
const isRunning = ref(false);
const outcome = ref(null);

const targetOptions = computed(() =>
    datasetStore.columns.filter(
        (c) => !c.is_identifier && c.type !== 'datetime' && (['integer', 'float'].includes(c.type) || c.unique <= 12),
    ),
);

const featureOptions = computed(() =>
    datasetStore.columns.filter(
        (c) => !c.is_identifier && c.name !== target.value && c.type !== 'datetime' &&
            (['integer', 'float'].includes(c.type) || c.unique <= 20),
    ),
);

watch([selectedId, () => datasetStore.columns], () => {
    target.value = targetOptions.value[0]?.name ?? '';
    outcome.value = null;
}, { immediate: true });

// Fitur mengikuti target: semua kolom layak dicentang kecuali yang banyak kosong.
watch([target, () => datasetStore.columns], () => {
    features.value = featureOptions.value
        .filter((c) => (c.missing ?? 0) < 15)
        .map((c) => c.name);
}, { immediate: true });

const toggleFeature = (name) => {
    features.value = features.value.includes(name)
        ? features.value.filter((item) => item !== name)
        : [...features.value, name];
};

const toggleAlgorithm = (value) => {
    algorithms.value = algorithms.value.includes(value)
        ? algorithms.value.filter((item) => item !== value)
        : [...algorithms.value, value];
};

async function run() {
    if (!target.value || !features.value.length || !algorithms.value.length) {
        toast.push('Lengkapi target, fitur, dan minimal satu algoritma.', 'warning');

        return;
    }

    isRunning.value = true;

    try {
        const response = await api.models.autoMl(selectedId.value, {
            target: target.value,
            features: features.value,
            algorithms: algorithms.value,
        });

        outcome.value = response.data;
        toast.push(response.data.interpretation);
    } catch (error) {
        toast.push(error.message, 'warning');
    } finally {
        isRunning.value = false;
    }
}

const scoreLabel = computed(() => (outcome.value?.task === 'regression' ? 'R²' : 'Akurasi'));

const fmtScore = (value) =>
    value === null || value === undefined
        ? '—'
        : outcome.value?.task === 'regression' ? asDecimal(value) : asPercent(value);

const RESULT_COLUMNS = computed(() => [
    { key: 'label', label: 'Model' },
    { key: 'score', label: scoreLabel.value, align: 'right', numeric: true },
    ...(outcome.value?.task === 'classification'
        ? [
              { key: 'precision', label: 'Presisi', align: 'right', numeric: true },
              { key: 'recall', label: 'Recall', align: 'right', numeric: true },
              { key: 'f1', label: 'F1', align: 'right', numeric: true },
          ]
        : [
              { key: 'rmse', label: 'RMSE', align: 'right', numeric: true },
              { key: 'mae', label: 'MAE', align: 'right', numeric: true },
          ]),
    { key: 'training_time_ms', label: 'Waktu Latih', align: 'right', numeric: true },
    { key: 'prediction_time_ms', label: 'Waktu Prediksi', align: 'right', numeric: true },
]);

const FIELD =
    'focus-ring h-9 w-full rounded-lg border-hairline bg-plane py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark';
</script>

<template>
    <PageHeader
        title="AutoML"
        description="Sistem mencoba beberapa algoritma sekaligus pada pembagian data yang sama, membandingkan performanya, dan memilih model terbaik."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'AutoML' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
            <AppButton variant="primary" icon="play" :disabled="isRunning" @click="run">
                {{ isRunning ? 'Melatih…' : `Jalankan AutoML (${algorithms.length})` }}
            </AppButton>
        </template>
    </PageHeader>

    <AppCard
        title="Konfigurasi"
        subtitle="Target menentukan jenis tugas: kategorikal = klasifikasi, numerik = regresi. 20% data ditahan sebagai data uji."
    >
        <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div>
                <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Target</label>
                <select v-model="target" :class="FIELD">
                    <option v-for="c in targetOptions" :key="c.name" :value="c.name">{{ c.name }} ({{ c.type }})</option>
                </select>
            </div>

            <div class="lg:col-span-2">
                <p class="mb-1.5 text-xs font-medium text-ink-2 dark:text-ink-2-dark">
                    Algoritma yang dicoba ({{ algorithms.length }})
                </p>
                <div class="flex flex-wrap gap-2">
                    <button
                        v-for="item in ALGORITHMS"
                        :key="item.value"
                        type="button"
                        class="focus-ring rounded-lg px-3 py-1.5 text-xs font-medium ring-1 ring-inset transition-colors"
                        :class="algorithms.includes(item.value)
                            ? 'bg-accent text-white ring-accent dark:bg-accent-dark dark:ring-accent-dark'
                            : 'text-ink-2 ring-hairline hover:bg-plane dark:text-ink-2-dark dark:ring-hairline-dark dark:hover:bg-raised-dark'"
                        :aria-pressed="algorithms.includes(item.value)"
                        @click="toggleAlgorithm(item.value)"
                    >
                        {{ item.label }}
                    </button>
                </div>
            </div>
        </div>

        <div class="mt-4">
            <p class="mb-1.5 text-xs font-medium text-ink-2 dark:text-ink-2-dark">
                Fitur ({{ features.length }} dari {{ featureOptions.length }})
            </p>
            <div class="flex flex-wrap gap-2">
                <button
                    v-for="c in featureOptions"
                    :key="c.name"
                    type="button"
                    class="focus-ring rounded-lg px-3 py-1.5 text-xs font-medium ring-1 ring-inset transition-colors"
                    :class="features.includes(c.name)
                        ? 'bg-accent text-white ring-accent dark:bg-accent-dark dark:ring-accent-dark'
                        : 'text-ink-2 ring-hairline hover:bg-plane dark:text-ink-2-dark dark:ring-hairline-dark dark:hover:bg-raised-dark'"
                    :aria-pressed="features.includes(c.name)"
                    @click="toggleFeature(c.name)"
                >
                    {{ c.name }}
                </button>
            </div>
        </div>
    </AppCard>

    <AppCard v-if="!outcome" class="mt-4" flush>
        <EmptyState
            icon="automl"
            title="Belum ada perbandingan"
            description="Jalankan AutoML untuk melatih seluruh algoritma terpilih dan melihat mana yang terbaik untuk dataset ini."
        />
    </AppCard>

    <template v-else>
        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <AppCard title="Model Terbaik" :subtitle="outcome.interpretation">
                <p class="text-2xl font-semibold text-ink dark:text-ink-dark">{{ outcome.best.label }}</p>
                <div class="mt-3 flex flex-wrap gap-2">
                    <AppBadge variant="good">{{ scoreLabel }} {{ fmtScore(outcome.best.score) }}</AppBadge>
                    <AppBadge>latih {{ outcome.best.training_time_ms }} ms</AppBadge>
                    <AppBadge>prediksi {{ outcome.best.prediction_time_ms }} ms</AppBadge>
                </div>
                <template #footer>
                    <RouterLink
                        :to="{ name: 'model-comparison.index' }"
                        class="focus-ring rounded text-xs font-medium text-accent hover:underline dark:text-accent-dark"
                    >
                        Lihat semua model di Model Comparison
                    </RouterLink>
                </template>
            </AppCard>

            <div class="lg:col-span-2">
                <ChartPanel
                    v-if="outcome.best.feature_importance?.length"
                    title="Feature Importance (model terbaik)"
                    subtitle="Kontribusi tiap fitur pada prediksi"
                    type="bar"
                    horizontal
                    :labels="outcome.best.feature_importance.slice(0, 8).map((f) => f.feature)"
                    :series="[{ label: 'Kontribusi', data: outcome.best.feature_importance.slice(0, 8).map((f) => Number(f.importance.toFixed(4))) }]"
                    :height="260"
                />
            </div>
        </div>

        <AppCard
            class="mt-4"
            title="Hasil Seluruh Algoritma"
            :subtitle="`${outcome.results.length} algoritma pada ${outcome.train_size} baris latih / ${outcome.test_size} baris uji · target ${outcome.target}`"
            flush
        >
            <DataTable :columns="RESULT_COLUMNS" :rows="outcome.results" row-key="algorithm">
                <template #cell-label="{ row }">
                    <span class="flex items-center gap-2">
                        <span class="font-medium text-ink dark:text-ink-dark">{{ row.label }}</span>
                        <AppBadge v-if="row.algorithm === outcome.best.algorithm" variant="good">Terbaik</AppBadge>
                        <AppBadge v-if="row.status === 'failed'" variant="critical">Gagal</AppBadge>
                    </span>
                </template>
                <template #cell-score="{ row }">
                    <span class="font-medium text-ink dark:text-ink-dark">{{ fmtScore(row.score) }}</span>
                </template>
                <template #cell-precision="{ row }">{{ row.metrics ? asPercent(row.metrics.precision) : '—' }}</template>
                <template #cell-recall="{ row }">{{ row.metrics ? asPercent(row.metrics.recall) : '—' }}</template>
                <template #cell-f1="{ row }">{{ row.metrics ? asPercent(row.metrics.f1) : '—' }}</template>
                <template #cell-rmse="{ row }">{{ row.metrics?.rmse ? Math.round(row.metrics.rmse).toLocaleString('id-ID') : '—' }}</template>
                <template #cell-mae="{ row }">{{ row.metrics?.mae ? Math.round(row.metrics.mae).toLocaleString('id-ID') : '—' }}</template>
                <template #cell-training_time_ms="{ row }">{{ row.training_time_ms != null ? `${row.training_time_ms} ms` : '—' }}</template>
                <template #cell-prediction_time_ms="{ row }">{{ row.prediction_time_ms != null ? `${row.prediction_time_ms} ms` : '—' }}</template>
            </DataTable>
        </AppCard>
    </template>
</template>
