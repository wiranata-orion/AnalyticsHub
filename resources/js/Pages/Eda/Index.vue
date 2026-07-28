<script setup>
import { computed, ref, watch } from 'vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import ProgressMeter from '@/Components/UI/ProgressMeter.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import BoxPlot from '@/Components/Charts/BoxPlot.vue';
import CorrelationHeatmap from '@/Components/Charts/CorrelationHeatmap.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useToastStore } from '@/stores/toast';
import { useDatasetStore } from '@/stores/dataset';
import { storeToRefs } from 'pinia';
import { api } from '@/Utils/api';
import { formatNumber } from '@/Utils/profiler';

/*
 * Exploratory Data Analysis: delapan sudut pandang atas dataset yang sama,
 * dihitung engine Python (python/eda/analysis.py) lewat REST API.
 *
 * Satu halaman dengan pemilih mode, bukan delapan halaman: pengguna EDA
 * berpindah-pindah sudut pandang dengan cepat, dan konteks datasetnya sama.
 * Hasil per mode di-cache selama sesi supaya berpindah mode tidak menghitung
 * ulang.
 */
const datasetStore = useDatasetStore();
const toast = useToastStore();
const { selectedId } = storeToRefs(datasetStore);

const MODES = [
    { value: 'univariate', label: 'Univariate', hint: 'Satu kolom: sebaran, ringkasan, frekuensi.' },
    { value: 'bivariate', label: 'Bivariate', hint: 'Hubungan dua kolom, otomatis menyesuaikan tipenya.' },
    { value: 'multivariate', label: 'Multivariate', hint: 'Beberapa kolom sekaligus lewat proyeksi PCA.' },
    { value: 'correlation', label: 'Correlation', hint: 'Matriks korelasi + pasangan terkuat.' },
    { value: 'distribution', label: 'Distribution', hint: 'Bentuk sebaran + uji normalitas.' },
    { value: 'pairplot', label: 'Pair Plot', hint: 'Matriks scatter antar kolom numerik.' },
    { value: 'missing_pattern', label: 'Missing Pattern', hint: 'Pola kekosongan, bukan sekadar jumlahnya.' },
    { value: 'feature_relationship', label: 'Feature Relationship', hint: 'Kekuatan tiap kolom terhadap target.' },
];

const mode = ref('univariate');
const results = ref({});
const isRunning = ref(false);

const result = computed(() => results.value[`${selectedId.value}:${mode.value}`] ?? null);

const numericColumns = computed(() =>
    datasetStore.columns.filter((c) => ['integer', 'float'].includes(c.type) && !c.is_identifier),
);
const categoricalColumns = computed(() =>
    datasetStore.columns.filter((c) => c.type === 'category' && !c.is_identifier && c.unique <= 20),
);
const allColumns = computed(() => datasetStore.columns.filter((c) => !c.is_identifier));

const params = ref({ column: '', x: '', y: '', color: '', method: 'pearson', target: '' });

// Pilihan kolom disegarkan saat dataset berganti agar tidak menunjuk kolom
// milik dataset sebelumnya.
watch([selectedId, () => datasetStore.columns], () => {
    params.value = {
        column: numericColumns.value[0]?.name ?? allColumns.value[0]?.name ?? '',
        x: numericColumns.value[0]?.name ?? '',
        y: numericColumns.value[1]?.name ?? numericColumns.value[0]?.name ?? '',
        color: '',
        method: 'pearson',
        target: categoricalColumns.value[0]?.name ?? numericColumns.value[0]?.name ?? '',
    };
}, { immediate: true });

function payload() {
    switch (mode.value) {
        case 'univariate':
            return { column: params.value.column };
        case 'bivariate':
            return { x: params.value.x, y: params.value.y };
        case 'multivariate':
            return params.value.color ? { color: params.value.color } : {};
        case 'correlation':
            return { method: params.value.method };
        case 'pairplot':
            return params.value.color ? { color: params.value.color } : {};
        case 'feature_relationship':
            return { target: params.value.target };
        default:
            return {};
    }
}

async function run() {
    if (!selectedId.value) {
        toast.push('Pilih dataset terlebih dahulu.', 'warning');

        return;
    }

    isRunning.value = true;

    try {
        const response = await api.analysis.run(selectedId.value, mode.value, payload());

        results.value[`${selectedId.value}:${mode.value}`] = response.data;
    } catch (error) {
        toast.push(error.message, 'warning');
    } finally {
        isRunning.value = false;
    }
}

const fmt = (value) => (value === null || value === undefined ? '—' : formatNumber(Number(value)));

const FIELD =
    'focus-ring h-9 w-full rounded-lg border-hairline bg-plane py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark';
</script>

<template>
    <PageHeader
        title="Exploratory Data Analysis"
        description="Kenali dataset sebelum mining dan machine learning: sebaran, hubungan antar kolom, pola kekosongan, dan kekuatan fitur."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'EDA' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
            <AppButton variant="primary" icon="play" :disabled="isRunning" @click="run">
                {{ isRunning ? 'Menganalisis…' : 'Jalankan Analisis' }}
            </AppButton>
        </template>
    </PageHeader>

    <!-- Pemilih mode -->
    <div class="mb-4 flex flex-wrap gap-2">
        <button
            v-for="item in MODES"
            :key="item.value"
            type="button"
            class="focus-ring rounded-lg px-3 py-1.5 text-xs font-medium ring-1 ring-inset transition-colors"
            :class="mode === item.value
                ? 'bg-accent text-white ring-accent dark:bg-accent-dark dark:ring-accent-dark'
                : 'text-ink-2 ring-hairline hover:bg-plane dark:text-ink-2-dark dark:ring-hairline-dark dark:hover:bg-raised-dark'"
            :aria-pressed="mode === item.value"
            :title="item.hint"
            @click="mode = item.value"
        >
            {{ item.label }}
        </button>
    </div>

    <!-- Parameter per mode -->
    <AppCard class="mb-4" :title="MODES.find((m) => m.value === mode)?.label" :subtitle="MODES.find((m) => m.value === mode)?.hint">
        <div class="grid grid-cols-1 items-end gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div v-if="mode === 'univariate'">
                <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Kolom</label>
                <select v-model="params.column" :class="FIELD">
                    <option v-for="c in allColumns" :key="c.name" :value="c.name">{{ c.name }} ({{ c.type }})</option>
                </select>
            </div>

            <template v-if="mode === 'bivariate'">
                <div>
                    <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Kolom X</label>
                    <select v-model="params.x" :class="FIELD">
                        <option v-for="c in allColumns" :key="c.name" :value="c.name">{{ c.name }} ({{ c.type }})</option>
                    </select>
                </div>
                <div>
                    <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Kolom Y</label>
                    <select v-model="params.y" :class="FIELD">
                        <option v-for="c in allColumns" :key="c.name" :value="c.name">{{ c.name }} ({{ c.type }})</option>
                    </select>
                </div>
            </template>

            <div v-if="['multivariate', 'pairplot'].includes(mode)">
                <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Warna per kategori (opsional)</label>
                <select v-model="params.color" :class="FIELD">
                    <option value="">Tanpa warna</option>
                    <option v-for="c in categoricalColumns" :key="c.name" :value="c.name">{{ c.name }}</option>
                </select>
            </div>

            <div v-if="mode === 'correlation'">
                <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Metode</label>
                <select v-model="params.method" :class="FIELD">
                    <option value="pearson">Pearson (linear)</option>
                    <option value="spearman">Spearman (peringkat)</option>
                    <option value="kendall">Kendall</option>
                </select>
            </div>

            <div v-if="mode === 'feature_relationship'">
                <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Kolom Target</label>
                <select v-model="params.target" :class="FIELD">
                    <option v-for="c in [...categoricalColumns, ...numericColumns]" :key="c.name" :value="c.name">
                        {{ c.name }} ({{ c.type }})
                    </option>
                </select>
            </div>

            <AppButton variant="primary" icon="play" :disabled="isRunning" @click="run">
                {{ isRunning ? 'Menganalisis…' : 'Jalankan' }}
            </AppButton>
        </div>
    </AppCard>

    <AppCard v-if="!result" flush>
        <EmptyState
            icon="eda"
            title="Belum ada hasil untuk mode ini"
            description="Atur parameter di atas lalu tekan Jalankan. Hasil tiap mode disimpan selama sesi, jadi berpindah mode tidak menghitung ulang."
        />
    </AppCard>

    <!-- ============ Hasil per mode ============ -->
    <template v-else-if="mode === 'univariate'">
        <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <AppCard :title="`Ringkasan ${result.column}`" :subtitle="`${result.count.toLocaleString('id-ID')} nilai terisi · ${result.missing} kosong · ${result.unique} unik`">
                <dl v-if="result.summary" class="space-y-2.5">
                    <div
                        v-for="row in [
                            ['Mean', fmt(result.summary.mean)], ['Median', fmt(result.summary.median)],
                            ['Std Dev', fmt(result.summary.std)], ['Min', fmt(result.summary.min)],
                            ['Maks', fmt(result.summary.max)], ['Q1', fmt(result.summary.q1)], ['Q3', fmt(result.summary.q3)],
                            ['Skewness', result.summary.skewness?.toFixed(2)?.replace('.', ',') ?? '—'],
                            ['Kurtosis', result.summary.kurtosis?.toFixed(2)?.replace('.', ',') ?? '—'],
                        ]"
                        :key="row[0]"
                        class="flex items-center justify-between gap-3 text-sm"
                    >
                        <dt class="text-ink-2 dark:text-ink-2-dark">{{ row[0] }}</dt>
                        <dd class="font-medium tabular-nums text-ink dark:text-ink-dark">{{ row[1] }}</dd>
                    </div>
                </dl>
                <p v-else class="text-sm text-ink-2 dark:text-ink-2-dark">
                    Modus: <span class="font-medium text-ink dark:text-ink-dark">{{ result.mode }}</span>
                </p>
            </AppCard>

            <div class="lg:col-span-2">
                <ChartPanel
                    v-if="result.histogram"
                    :title="`Histogram ${result.column}`"
                    subtitle="Frekuensi per rentang nilai"
                    type="bar"
                    :labels="result.histogram.labels"
                    :series="[{ label: 'Frekuensi', data: result.histogram.counts }]"
                    :height="280"
                />
                <ChartPanel
                    v-else-if="result.frequency"
                    :title="`Frekuensi ${result.column}`"
                    subtitle="Jumlah baris per kategori"
                    type="bar"
                    horizontal
                    :labels="result.frequency.labels"
                    :series="[{ label: 'Jumlah', data: result.frequency.counts }]"
                    :height="280"
                />
            </div>
        </div>

        <AppCard v-if="result.boxplot" class="mt-4" title="Boxplot" subtitle="Ringkasan lima angka dan nilai ekstrem">
            <BoxPlot :boxes="[{ label: result.column, ...result.boxplot, lowerFence: result.boxplot.lower_fence, upperFence: result.boxplot.upper_fence, outlierCount: result.boxplot.outlier_count }]" />
        </AppCard>
    </template>

    <template v-else-if="mode === 'bivariate'">
        <ChartPanel
            v-if="result.mode === 'numeric_numeric'"
            :title="`${result.y} terhadap ${result.x}`"
            :subtitle="result.interpretation"
            type="scatter"
            :series="[{ label: `${result.y} vs ${result.x}`, data: result.points }]"
            :height="340"
        />
        <AppCard
            v-else-if="result.mode === 'category_numeric'"
            :title="`${result.y} per ${result.x}`"
            subtitle="Ringkasan nilai per kelompok"
            flush
        >
            <DataTable
                :columns="[
                    { key: 'label', label: result.x },
                    { key: 'count', label: 'N', align: 'right', numeric: true },
                    { key: 'mean', label: 'Mean', align: 'right', numeric: true },
                    { key: 'median', label: 'Median', align: 'right', numeric: true },
                    { key: 'min', label: 'Min', align: 'right', numeric: true },
                    { key: 'max', label: 'Maks', align: 'right', numeric: true },
                ]"
                :rows="result.groups"
                row-key="label"
            >
                <template v-for="key in ['mean', 'median', 'min', 'max']" #[`cell-${key}`]="{ row }" :key="key">
                    {{ fmt(row[key]) }}
                </template>
            </DataTable>
        </AppCard>
        <AppCard v-else :title="`${result.x} × ${result.y}`" :subtitle="result.interpretation">
            <div class="mb-3 flex flex-wrap gap-2">
                <AppBadge>Chi² = {{ result.chi_square?.toFixed(2)?.replace('.', ',') }}</AppBadge>
                <AppBadge>p = {{ result.p_value?.toExponential(2) }}</AppBadge>
                <AppBadge>Cramér's V = {{ result.cramers_v?.toFixed(2)?.replace('.', ',') }}</AppBadge>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full table-fixed border-separate border-spacing-0.5 text-xs">
                    <thead>
                        <tr>
                            <th />
                            <th v-for="column in result.columns" :key="column" class="truncate px-1 pb-1 text-center font-medium text-ink-3">{{ column }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, index) in result.matrix" :key="result.rows[index]">
                            <th class="truncate pr-2 text-right font-medium text-ink-2 dark:text-ink-2-dark">{{ result.rows[index] }}</th>
                            <td v-for="(value, col) in row" :key="col" class="h-8 rounded bg-plane text-center tabular-nums text-ink dark:bg-raised-dark dark:text-ink-dark">
                                {{ value }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </AppCard>
    </template>

    <template v-else-if="mode === 'multivariate'">
        <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div class="lg:col-span-2">
                <ChartPanel
                    title="Proyeksi PCA"
                    :subtitle="result.interpretation"
                    type="scatter"
                    :series="result.series"
                    :height="340"
                />
            </div>
            <AppCard title="Kontribusi Kolom" subtitle="Bobot tiap kolom pada dua komponen utama.">
                <div class="space-y-3">
                    <div v-for="loading in result.loadings" :key="loading.column" class="text-sm">
                        <p class="font-medium text-ink dark:text-ink-dark">{{ loading.column }}</p>
                        <p class="text-xs tabular-nums text-ink-3">
                            PC1 {{ loading.pc1.toFixed(2).replace('.', ',') }} · PC2 {{ loading.pc2.toFixed(2).replace('.', ',') }}
                        </p>
                    </div>
                </div>
            </AppCard>
        </div>
    </template>

    <template v-else-if="mode === 'correlation'">
        <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div class="lg:col-span-2">
                <AppCard title="Matriks Korelasi" :subtitle="`Metode ${result.method}`">
                    <CorrelationHeatmap :columns="result.columns" :matrix="result.matrix" />
                </AppCard>
            </div>
            <AppCard title="Pasangan Terkuat" flush>
                <ul>
                    <li
                        v-for="pair in result.top_pairs"
                        :key="`${pair.x}-${pair.y}`"
                        class="border-b border-hairline px-5 py-3 text-sm last:border-0 dark:border-hairline-dark"
                    >
                        <p class="font-medium text-ink dark:text-ink-dark">{{ pair.x }} ↔ {{ pair.y }}</p>
                        <p class="mt-0.5 text-xs text-ink-2 dark:text-ink-2-dark">{{ pair.interpretation }}</p>
                    </li>
                </ul>
            </AppCard>
        </div>
    </template>

    <template v-else-if="mode === 'distribution'">
        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChartPanel
                v-for="column in result.columns"
                :key="column.column"
                :title="`Sebaran ${column.column}`"
                :subtitle="column.interpretation"
                type="bar"
                :labels="column.histogram.labels"
                :series="[{ label: 'Frekuensi', data: column.histogram.counts }]"
                :height="240"
            >
                <template #actions>
                    <AppBadge :variant="column.is_normal ? 'good' : 'warning'">
                        {{ column.is_normal ? 'Normal' : 'Tidak normal' }}
                    </AppBadge>
                </template>
            </ChartPanel>
        </div>
    </template>

    <template v-else-if="mode === 'pairplot'">
        <AppCard
            title="Pair Plot"
            :subtitle="`${result.columns.length} kolom · ${result.sampled_rows.toLocaleString('id-ID')} baris sampel`"
        >
            <div
                class="grid gap-2"
                :style="{ gridTemplateColumns: `repeat(${result.columns.length}, minmax(0, 1fr))` }"
            >
                <div
                    v-for="cell in result.cells"
                    :key="`${cell.row}-${cell.column}`"
                    class="rounded-lg border border-hairline p-2 dark:border-hairline-dark"
                >
                    <p class="mb-1 truncate text-[10px] text-ink-3" :title="`${cell.row} × ${cell.column}`">
                        {{ cell.kind === 'histogram' ? cell.row : `${cell.row} × ${cell.column}` }}
                        <template v-if="cell.kind === 'scatter'"> · r {{ cell.correlation?.toFixed(2)?.replace('.', ',') }}</template>
                    </p>
                    <ChartPanel
                        v-if="cell.kind === 'histogram'"
                        type="bar"
                        :labels="cell.labels"
                        :series="[{ label: cell.row, data: cell.counts }]"
                        :height="110"
                    />
                    <ChartPanel
                        v-else
                        type="scatter"
                        :series="cell.series"
                        :height="110"
                    />
                </div>
            </div>
        </AppCard>
    </template>

    <template v-else-if="mode === 'missing_pattern'">
        <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <AppCard title="Kelengkapan Baris" :subtitle="result.interpretation">
                <p class="flex items-baseline gap-2">
                    <span class="text-4xl font-semibold text-ink dark:text-ink-dark">{{ result.complete_percent.toLocaleString('id-ID') }}%</span>
                    <span class="text-sm text-ink-3">baris lengkap</span>
                </p>
                <div class="mt-4 space-y-3">
                    <ProgressMeter
                        v-for="column in result.per_column.filter((c) => c.missing > 0).slice(0, 6)"
                        :key="column.column"
                        :label="column.column"
                        :value="100 - column.percent"
                        :caption="`${column.percent.toLocaleString('id-ID')}% kosong`"
                    />
                </div>
            </AppCard>

            <AppCard title="Kombinasi Kekosongan" subtitle="Pola kolom-kosong yang paling sering muncul bersamaan." flush>
                <DataTable
                    :columns="[
                        { key: 'pattern', label: 'Pola', wrap: true },
                        { key: 'rows', label: 'Baris', align: 'right', numeric: true },
                        { key: 'share', label: '%', align: 'right', numeric: true },
                    ]"
                    :rows="result.combinations"
                    row-key="pattern"
                />
            </AppCard>

            <AppCard title="Kekosongan yang Berkorelasi" subtitle="Nilai tinggi berarti dua kolom kosong bersamaan — biasanya satu proses yang gagal." flush>
                <DataTable
                    v-if="result.correlated_missing.length"
                    :columns="[
                        { key: 'x', label: 'Kolom A' },
                        { key: 'y', label: 'Kolom B' },
                        { key: 'value', label: 'Korelasi', align: 'right', numeric: true },
                    ]"
                    :rows="result.correlated_missing"
                    :row-key="'x'"
                />
                <EmptyState v-else icon="check" title="Tidak ada pola" description="Kekosongan antar kolom tidak saling terkait." />
            </AppCard>
        </div>
    </template>

    <template v-else-if="mode === 'feature_relationship'">
        <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div class="lg:col-span-2">
                <ChartPanel
                    :title="`Kekuatan fitur terhadap ${result.target}`"
                    :subtitle="result.interpretation"
                    type="bar"
                    horizontal
                    :labels="result.features.slice(0, 10).map((f) => f.feature)"
                    :series="[{ label: 'Mutual information', data: result.features.slice(0, 10).map((f) => Number(f.score.toFixed(4))) }]"
                    :height="320"
                />
            </div>
            <AppCard title="Rincian" :subtitle="`Tugas: ${result.task === 'classification' ? 'klasifikasi' : 'regresi'}`" flush>
                <DataTable
                    :columns="[
                        { key: 'feature', label: 'Fitur' },
                        { key: 'type', label: 'Tipe' },
                        { key: 'share', label: 'Kontribusi', align: 'right', numeric: true },
                    ]"
                    :rows="result.features"
                    row-key="feature"
                >
                    <template #cell-share="{ row }">{{ row.share.toLocaleString('id-ID') }}%</template>
                </DataTable>
            </AppCard>
        </div>
    </template>
</template>
