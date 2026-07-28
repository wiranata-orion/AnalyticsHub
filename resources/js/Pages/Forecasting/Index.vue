<script setup>
import { computed, ref, watch } from 'vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useAnalysis } from '@/Composables/useAnalysis';

/*
 * Forecasting: ARIMA, SARIMA, Holt-Winters, dan Prophet dijalankan pada deret
 * yang sama (python/forecasting/models.py). Akurasinya diukur pada periode uji
 * yang ditahan dari ekor deret, lalu model terbaik dipakai sebagai proyeksi.
 */
const { datasetStore, result, isRunning, isLoading, run } = useAnalysis('forecasting');

const MODELS = [
    { value: 'arima', label: 'ARIMA' },
    { value: 'sarima', label: 'SARIMA' },
    { value: 'holt_winters', label: 'Holt-Winters' },
    { value: 'prophet', label: 'Prophet' },
];

const timeColumn = ref('');
const valueColumn = ref('');
const horizon = ref(12);
const chosen = ref(MODELS.map((model) => model.value));

const timeColumns = computed(() => datasetStore.columns.filter((c) => c.type === 'datetime'));
const numericColumns = computed(() =>
    datasetStore.columns.filter((c) => ['integer', 'float'].includes(c.type) && !c.is_identifier),
);

watch([() => datasetStore.selectedId, () => datasetStore.columns], () => {
    timeColumn.value = timeColumns.value[0]?.name ?? '';
    valueColumn.value = numericColumns.value[0]?.name ?? '';
}, { immediate: true });

const toggleModel = (value) => {
    chosen.value = chosen.value.includes(value)
        ? chosen.value.filter((item) => item !== value)
        : [...chosen.value, value];
};

function runForecast() {
    run({
        time_column: timeColumn.value || undefined,
        value_column: valueColumn.value || undefined,
        horizon: Number(horizon.value),
        models: chosen.value,
    });
}

/*
 * Grafik gabungan: riwayat + proyeksi tiap model. Deret proyeksi diberi null
 * sepanjang riwayat supaya garisnya dimulai tepat setelah data terakhir.
 */
const chart = computed(() => {
    if (!result.value) {
        return null;
    }

    const history = result.value.history;
    const labels = [...history.labels, ...result.value.future_labels].map((label) => label.slice(0, 10));
    const padding = new Array(history.values.length - 1).fill(null);
    const lastValue = history.values[history.values.length - 1];

    const series = [{ label: result.value.value_column, data: [...history.values, ...new Array(result.value.future_labels.length).fill(null)] }];

    for (const model of result.value.results) {
        if (model.status !== 'ready') {
            continue;
        }

        series.push({
            label: `Proyeksi ${model.label}`,
            data: [...padding, lastValue, ...model.forecast],
        });
    }

    return { labels, series };
});

const metricRows = computed(() =>
    (result.value?.results ?? []).map((model) => ({
        id: model.model,
        label: model.label ?? model.model,
        status: model.status,
        rmse: model.metrics ? Math.round(model.metrics.rmse).toLocaleString('id-ID') : '—',
        mae: model.metrics ? Math.round(model.metrics.mae).toLocaleString('id-ID') : '—',
        mape: model.metrics?.mape != null ? `${model.metrics.mape.toFixed(1).replace('.', ',')}%` : '—',
        error: model.error ?? null,
    })),
);

const FIELD =
    'focus-ring h-9 w-full rounded-lg border-hairline bg-plane py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark';
</script>

<template>
    <PageHeader
        title="Forecasting"
        description="Proyeksikan deret waktu dengan ARIMA, SARIMA, Holt-Winters, dan Prophet — dievaluasi pada periode uji yang sama sebelum dipakai meramal."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Forecasting' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
            <AppButton variant="primary" icon="play" :disabled="isRunning" @click="runForecast">
                {{ isRunning ? 'Meramal…' : 'Jalankan Forecast' }}
            </AppButton>
        </template>
    </PageHeader>

    <AppCard
        v-if="!timeColumns.length"
        flush
    >
        <EmptyState
            icon="forecasting"
            title="Dataset ini tidak punya kolom waktu"
            description="Forecasting membutuhkan kolom bertipe tanggal/waktu. Pilih dataset lain, atau periksa apakah kolom tanggalnya terbaca sebagai teks di halaman Profiling."
        />
    </AppCard>

    <template v-else>
        <AppCard title="Konfigurasi" subtitle="Sebagian akhir deret ditahan sebagai data uji untuk mengukur akurasi tiap model.">
            <div class="grid grid-cols-1 items-end gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div>
                    <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Kolom Waktu</label>
                    <select v-model="timeColumn" :class="FIELD">
                        <option v-for="c in timeColumns" :key="c.name" :value="c.name">{{ c.name }}</option>
                    </select>
                </div>
                <div>
                    <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Kolom Nilai</label>
                    <select v-model="valueColumn" :class="FIELD">
                        <option v-for="c in numericColumns" :key="c.name" :value="c.name">{{ c.name }}</option>
                    </select>
                </div>
                <div>
                    <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Horizon (periode)</label>
                    <input v-model.number="horizon" type="number" min="1" max="120" :class="FIELD" />
                </div>
                <div>
                    <p class="mb-1.5 text-xs font-medium text-ink-2 dark:text-ink-2-dark">Model</p>
                    <div class="flex flex-wrap gap-1.5">
                        <button
                            v-for="model in MODELS"
                            :key="model.value"
                            type="button"
                            class="focus-ring rounded-lg px-2.5 py-1 text-xs font-medium ring-1 ring-inset transition-colors"
                            :class="chosen.includes(model.value)
                                ? 'bg-accent text-white ring-accent dark:bg-accent-dark dark:ring-accent-dark'
                                : 'text-ink-2 ring-hairline hover:bg-plane dark:text-ink-2-dark dark:ring-hairline-dark dark:hover:bg-raised-dark'"
                            :aria-pressed="chosen.includes(model.value)"
                            @click="toggleModel(model.value)"
                        >
                            {{ model.label }}
                        </button>
                    </div>
                </div>
            </div>
        </AppCard>

        <AppCard v-if="!result && !isLoading" class="mt-4" flush>
            <EmptyState
                icon="forecasting"
                title="Belum ada peramalan"
                description="Jalankan forecast untuk membandingkan model dan melihat proyeksi beberapa periode ke depan."
            />
        </AppCard>

        <template v-else-if="result">
            <ChartPanel
                v-if="chart"
                class="mt-4"
                :title="`${result.value_column} — riwayat dan proyeksi`"
                :subtitle="result.interpretation"
                type="line"
                :labels="chart.labels"
                :series="chart.series"
                :height="360"
            />

            <AppCard
                class="mt-4"
                title="Akurasi per Model"
                :subtitle="`Diukur pada ${result.holdout} periode uji terakhir · ${result.periods} periode total · frekuensi ${result.freq}`"
                flush
            >
                <DataTable
                    :columns="[
                        { key: 'label', label: 'Model' },
                        { key: 'rmse', label: 'RMSE', align: 'right', numeric: true },
                        { key: 'mae', label: 'MAE', align: 'right', numeric: true },
                        { key: 'mape', label: 'MAPE', align: 'right', numeric: true },
                        { key: 'error', label: 'Keterangan', wrap: true },
                    ]"
                    :rows="metricRows"
                >
                    <template #cell-label="{ row }">
                        <span class="flex items-center gap-2">
                            <span class="font-medium text-ink dark:text-ink-dark">{{ row.label }}</span>
                            <AppBadge v-if="row.id === result.best" variant="good">Terbaik</AppBadge>
                            <AppBadge v-if="row.status === 'failed'" variant="critical">Gagal</AppBadge>
                        </span>
                    </template>
                    <template #cell-error="{ row }">
                        <span class="text-xs text-ink-3">{{ row.error ?? 'RMSE terendah = paling akurat pada data uji.' }}</span>
                    </template>
                </DataTable>
            </AppCard>
        </template>
    </template>
</template>
