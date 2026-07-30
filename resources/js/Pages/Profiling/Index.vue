<script setup>
import { computed, ref } from 'vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import StatTile from '@/Components/UI/StatTile.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import ProgressMeter from '@/Components/UI/ProgressMeter.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import CorrelationHeatmap from '@/Components/Charts/CorrelationHeatmap.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useAnalysis } from '@/Composables/useAnalysis';
import { useToastStore } from '@/stores/toast';
import { api } from '@/Utils/api';
import { formatNumber } from '@/Utils/profiler';
import { downloadCsv } from '@/Utils/exportCsv';

/*
 * Profil dataset dari hasil profiling server (tabel dataset_columns), plus
 * matriks korelasi lewat endpoint analisis. Tidak ada perhitungan di peramban.
 */
const correlation = useAnalysis('correlation');
const datasetStore = correlation.datasetStore;
const toast = useToastStore();
const isReprofiling = ref(false);

const columns = computed(() => datasetStore.columns);
const detail = computed(() => datasetStore.selectedDetail);

const summary = computed(() => {
    if (!detail.value) {
        return [];
    }

    const totalMissing = columns.value.reduce((sum, c) => sum + (c.missing_count ?? 0), 0);
    const cells = (detail.value.rows ?? 0) * (detail.value.columns_count ?? 1);
    const outliers = columns.value.reduce((sum, c) => sum + (c.outlier_count ?? 0), 0);

    return [
        { label: 'Jumlah Baris', value: detail.value.rows?.toLocaleString('id-ID') ?? '—', icon: 'table' },
        { label: 'Jumlah Kolom', value: String(detail.value.columns_count ?? '—'), icon: 'datasets' },
        { label: 'Sel Kosong', value: cells ? `${((totalMissing / cells) * 100).toFixed(1).replace('.', ',')}` : '—', unit: '%', icon: 'warning' },
        { label: 'Total Outlier', value: outliers.toLocaleString('id-ID'), icon: 'trendUp' },
    ];
});

const missingChart = computed(() => {
    const worst = [...columns.value]
        .filter((c) => c.missing > 0)
        .sort((a, b) => b.missing - a.missing)
        .slice(0, 5);

    return worst.length
        ? {
              labels: worst.map((c) => c.name),
              series: [{ label: 'Missing', data: worst.map((c) => Number(c.missing.toFixed(2))) }],
          }
        : null;
});

const typeChart = computed(() => {
    const tally = {};

    for (const column of columns.value) {
        const label = ['integer', 'float'].includes(column.type)
            ? 'Numerik'
            : column.type === 'category' ? 'Kategori'
            : column.type === 'datetime' ? 'Tanggal' : 'Teks';

        tally[label] = (tally[label] ?? 0) + 1;
    }

    return {
        labels: Object.keys(tally),
        series: [{ label: 'Kolom', data: Object.values(tally) }],
    };
});

async function reprofile() {
    if (!datasetStore.selectedId) {
        return;
    }

    isReprofiling.value = true;

    try {
        const response = await api.datasets.reprofile(datasetStore.selectedId);

        datasetStore.details[datasetStore.selectedId] = response.data;
        toast.push('Profiling selesai dijalankan ulang.');
    } catch (error) {
        toast.push(error.message, 'warning');
    } finally {
        isReprofiling.value = false;
    }
}

function exportColumns() {
    downloadCsv(
        'profil_kolom.csv',
        ['Kolom', 'Tipe', 'Missing %', 'Unik', 'Mean', 'Std', 'Outlier'],
        columns.value.map((c) => [c.name, c.type, c.missing, c.unique, c.mean ?? '', c.std ?? '', c.outlier_count]),
    );
    toast.push('Profil kolom diekspor sebagai CSV.');
}

const COLUMN_TABLE = [
    { key: 'name', label: 'Kolom' },
    { key: 'type', label: 'Tipe' },
    { key: 'missing', label: 'Missing', align: 'right', numeric: true },
    { key: 'unique', label: 'Nilai Unik', align: 'right', numeric: true },
    { key: 'mean', label: 'Rata-rata', align: 'right', numeric: true },
    { key: 'std', label: 'Simpangan Baku', align: 'right', numeric: true },
    { key: 'skewness', label: 'Skewness', align: 'right', numeric: true },
    { key: 'outlier_count', label: 'Outlier', align: 'right', numeric: true },
];

const fmt = (value) => (value === null || value === undefined ? '—' : formatNumber(Number(value)));
</script>

<template>
    <PageHeader
        title="Data Profiling"
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Profiling' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
            <AppButton 
                variant="primary" 
                icon="refresh" 
                :disabled="isReprofiling || isLoading || !datasetStore.selectedId" 
                @click="reprofile"
            >
                {{ isReprofiling ? 'Memproses…' : 'Jalankan Ulang' }}
            </AppButton>
        </template>
    </PageHeader>

    <AppCard v-if="!detail && !datasetStore.isLoading" flush>
        <EmptyState
            icon="profiling"
            title="Belum ada dataset terpilih"
        />
    </AppCard>

    <template v-else-if="detail">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile
                v-for="item in summary"
                :key="item.label"
                :label="item.label"
                :value="item.value"
                :unit="item.unit ?? null"
                :icon="item.icon"
            />
        </div>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div class="lg:col-span-2">
                <ChartPanel
                    v-if="missingChart"
                    title="Missing Value per Kolom"
                    subtitle="Lima kolom dengan nilai kosong terbanyak"
                    type="bar"
                    horizontal
                    :labels="missingChart.labels"
                    :series="missingChart.series"
                    value-suffix="%"
                    :height="240"
                />
                <AppCard v-else title="Missing Value per Kolom">
                    <EmptyState icon="check" title="Tidak ada sel kosong" description="Seluruh kolom terisi penuh." />
                </AppCard>
            </div>

            <ChartPanel
                title="Komposisi Tipe Data"
                type="doughnut"
                :labels="typeChart.labels"
                :series="typeChart.series"
                :height="240"
            />
        </div>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div class="lg:col-span-2">
                <AppCard
                    title="Matriks Korelasi"
                    subtitle="Koefisien Pearson antar kolom numerik — dihitung engine Python."
                >
                    <template #actions>
                        <AppButton size="sm" icon="play" :disabled="correlation.isRunning.value" @click="correlation.run()">
                            {{ correlation.isRunning.value ? 'Menghitung…' : 'Hitung' }}
                        </AppButton>
                    </template>

                    <CorrelationHeatmap
                        v-if="correlation.result.value"
                        :columns="correlation.result.value.columns"
                        :matrix="correlation.result.value.matrix"
                    />
                    <EmptyState
                        v-else
                        icon="profiling"
                        title="Belum dihitung"
                        description="Tekan Hitung untuk membangun matriks korelasi kolom numerik."
                    />
                </AppCard>
            </div>

            <AppCard title="Kelengkapan Data" subtitle="Proporsi sel terisi per kolom bermasalah">
                <div v-if="columns.some((c) => c.missing > 0)" class="space-y-4">
                    <ProgressMeter
                        v-for="column in columns.filter((c) => c.missing > 0)"
                        :key="column.name"
                        :label="column.name"
                        :value="100 - column.missing"
                        :caption="`${(100 - column.missing).toFixed(1).replace('.', ',')}% terisi`"
                    />
                </div>
                <EmptyState v-else icon="check" title="Lengkap" description="Tidak ada kolom dengan sel kosong." />
            </AppCard>
        </div>

        <AppCard class="mt-4" title="Profil per Kolom" flush>
            <template #actions>
                <AppButton size="sm" icon="download" @click="exportColumns">Ekspor CSV</AppButton>
            </template>

            <DataTable :columns="COLUMN_TABLE" :rows="columns" row-key="name">
                <template #cell-name="{ row }">
                    <span class="flex items-center gap-2 font-medium text-ink dark:text-ink-dark">
                        {{ row.name }}
                        <AppBadge v-if="row.is_identifier" variant="neutral">ID</AppBadge>
                    </span>
                </template>
                <template #cell-type="{ row }">
                    <AppBadge :variant="['integer', 'float'].includes(row.type) ? 'info' : 'neutral'">
                        {{ row.type }}
                    </AppBadge>
                </template>
                <template #cell-missing="{ row }">
                    <AppBadge :variant="row.missing === 0 ? 'good' : row.missing < 5 ? 'warning' : 'critical'">
                        {{ row.missing.toFixed(1).replace('.', ',') }}%
                    </AppBadge>
                </template>
                <template #cell-unique="{ row }">{{ row.unique.toLocaleString('id-ID') }}</template>
                <template #cell-mean="{ row }">{{ fmt(row.mean) }}</template>
                <template #cell-std="{ row }">{{ fmt(row.std) }}</template>
                <template #cell-skewness="{ row }">
                    {{ row.skewness != null ? row.skewness.toFixed(2).replace('.', ',') : '—' }}
                </template>
                <template #cell-outlier_count="{ row }">
                    <span :class="row.outlier_count > 0 ? 'text-ink dark:text-ink-dark' : 'text-ink-3'">
                        {{ row.outlier_count.toLocaleString('id-ID') }}
                    </span>
                </template>
            </DataTable>
        </AppCard>
    </template>
</template>
