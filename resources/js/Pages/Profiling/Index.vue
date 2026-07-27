<script setup>
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import StatTile from '@/Components/UI/StatTile.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import ProgressMeter from '@/Components/UI/ProgressMeter.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import CorrelationHeatmap from '@/Components/Charts/CorrelationHeatmap.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { profiling } from '@/data/placeholder';

const { summary, columns, missingByColumn, typeDistribution, correlation } =
    profiling;

const COLUMN_TABLE = [
    { key: 'name', label: 'Kolom' },
    { key: 'type', label: 'Tipe' },
    { key: 'missing', label: 'Missing', align: 'right', numeric: true },
    { key: 'unique', label: 'Nilai Unik', align: 'right', numeric: true },
    { key: 'mean', label: 'Rata-rata', align: 'right', numeric: true },
    { key: 'std', label: 'Simpangan Baku', align: 'right', numeric: true },
    { key: 'outliers', label: 'Outlier', align: 'right', numeric: true },
];

const TYPE_VARIANTS = {
    integer: 'info',
    float: 'info',
    datetime: 'neutral',
    category: 'neutral',
    text: 'neutral',
};

// Ambang yang sama dipakai untuk mewarnai badge dan memutuskan nada peringatan.
function missingVariant(percentage) {
    if (percentage === 0) {
        return 'good';
    }

    if (percentage < 5) {
        return 'warning';
    }

    return 'critical';
}
</script>

<template>
    <AppLayout>
        <PageHeader
            title="Data Profiling"
            description="Karakteristik dataset: tipe data, kelengkapan, sebaran, dan hubungan antar kolom."
            :breadcrumbs="[
                { label: 'Dashboard', to: { name: 'dashboard' } },
                { label: 'Profiling' },
            ]"
        >
            <template #actions>
                <DatasetSelector />
                <AppButton variant="primary" icon="refresh">
                    Jalankan Ulang
                </AppButton>
            </template>
        </PageHeader>

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
                    title="Missing Value per Kolom"
                    subtitle="Lima kolom dengan nilai kosong terbanyak"
                    type="bar"
                    horizontal
                    :labels="missingByColumn.labels"
                    :series="missingByColumn.series"
                    value-suffix="%"
                    :height="240"
                />
            </div>

            <ChartPanel
                title="Komposisi Tipe Data"
                type="doughnut"
                :labels="typeDistribution.labels"
                :series="typeDistribution.series"
                :height="240"
            />
        </div>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div class="lg:col-span-2">
                <AppCard
                    title="Matriks Korelasi"
                    subtitle="Koefisien Pearson antar kolom numerik"
                >
                    <CorrelationHeatmap
                        :columns="correlation.columns"
                        :matrix="correlation.matrix"
                    />
                </AppCard>
            </div>

            <AppCard
                title="Kelengkapan Data"
                subtitle="Proporsi sel terisi per kolom bermasalah"
            >
                <div class="space-y-4">
                    <ProgressMeter
                        v-for="column in columns.filter((c) => c.missing > 0)"
                        :key="column.name"
                        :label="column.name"
                        :value="100 - column.missing"
                        :caption="`${(100 - column.missing).toFixed(1).replace('.', ',')}% terisi`"
                    />
                </div>
            </AppCard>
        </div>

        <AppCard class="mt-4" title="Profil per Kolom" flush>
            <template #actions>
                <AppButton size="sm" icon="download">Ekspor CSV</AppButton>
            </template>

            <DataTable :columns="COLUMN_TABLE" :rows="columns" row-key="name">
                <template #cell-name="{ row }">
                    <span class="font-medium text-ink dark:text-ink-dark">
                        {{ row.name }}
                    </span>
                </template>

                <template #cell-type="{ row }">
                    <AppBadge :variant="TYPE_VARIANTS[row.type] ?? 'neutral'">
                        {{ row.type }}
                    </AppBadge>
                </template>

                <template #cell-missing="{ row }">
                    <AppBadge :variant="missingVariant(row.missing)">
                        {{ row.missing.toFixed(1).replace('.', ',') }}%
                    </AppBadge>
                </template>

                <template #cell-unique="{ row }">
                    {{ row.unique.toLocaleString('id-ID') }}
                </template>

                <template #cell-outliers="{ row }">
                    <span
                        :class="
                            row.outliers > 0
                                ? 'text-ink dark:text-ink-dark'
                                : 'text-ink-3'
                        "
                    >
                        {{ row.outliers.toLocaleString('id-ID') }}
                    </span>
                </template>
            </DataTable>
        </AppCard>
    </AppLayout>
</template>
