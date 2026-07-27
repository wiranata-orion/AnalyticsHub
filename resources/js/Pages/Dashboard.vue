<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import StatTile from '@/Components/UI/StatTile.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import StatusBadge from '@/Components/UI/StatusBadge.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import { useDatasetStore } from '@/stores/dataset';
import { dashboard } from '@/data/placeholder';

const datasetStore = useDatasetStore();

const { stats, activityTrend, jobDistribution, insights } = dashboard;
const recentDatasets = computed(() => datasetStore.items.slice(0, 4));

const DATASET_COLUMNS = [
    { key: 'name', label: 'Nama Dataset' },
    { key: 'rows', label: 'Baris', align: 'right', numeric: true },
    { key: 'columns', label: 'Kolom', align: 'right', numeric: true },
    { key: 'size', label: 'Ukuran', align: 'right', numeric: true },
    { key: 'status', label: 'Status' },
    { key: 'updated_at', label: 'Diperbarui', align: 'right' },
];

const INSIGHT_TONES = {
    good: 'text-[#006300] dark:text-status-good',
    warning: 'text-[#8a5a00] dark:text-status-warning',
    serious: 'text-[#a34418] dark:text-status-serious',
    critical: 'text-status-critical',
};
</script>

<template>
    <AppLayout>
        <PageHeader
            title="Dashboard"
            description="Ringkasan dataset, analisis yang berjalan, dan temuan terbaru."
        >
            <template #actions>
                <AppButton icon="refresh">Muat Ulang</AppButton>
                <AppButton
                    variant="primary"
                    icon="upload"
                    :to="{ name: 'datasets.create' }"
                >
                    Upload Dataset
                </AppButton>
            </template>
        </PageHeader>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile
                v-for="stat in stats"
                :key="stat.label"
                :label="stat.label"
                :value="stat.value"
                :unit="stat.unit ?? null"
                :icon="stat.icon"
                :delta="stat.delta ?? null"
                :delta-label="stat.deltaLabel ?? 'vs bulan lalu'"
                :lower-is-better="stat.lowerIsBetter ?? false"
            />
        </div>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div class="lg:col-span-2">
                <ChartPanel
                    title="Aktivitas Platform"
                    subtitle="Tujuh bulan terakhir"
                    type="area"
                    :labels="activityTrend.labels"
                    :series="activityTrend.series"
                    :height="280"
                />
            </div>

            <ChartPanel
                title="Distribusi Job"
                subtitle="Berdasarkan jenis analisis"
                type="doughnut"
                :labels="jobDistribution.labels"
                :series="jobDistribution.series"
                :height="280"
            />
        </div>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div class="lg:col-span-2">
                <AppCard title="Dataset Terbaru" flush>
                    <template #actions>
                        <RouterLink
                            :to="{ name: 'datasets.index' }"
                            class="focus-ring rounded text-xs font-medium text-accent hover:underline dark:text-accent-dark"
                        >
                            Lihat semua
                        </RouterLink>
                    </template>

                    <DataTable :columns="DATASET_COLUMNS" :rows="recentDatasets">
                        <template #cell-name="{ row }">
                            <RouterLink
                                :to="{ name: 'datasets.show', params: { id: row.id } }"
                                class="focus-ring rounded font-medium text-ink hover:text-accent dark:text-ink-dark dark:hover:text-accent-dark"
                            >
                                {{ row.name }}
                            </RouterLink>
                        </template>

                        <template #cell-status="{ row }">
                            <StatusBadge :status="row.status" />
                        </template>
                    </DataTable>
                </AppCard>
            </div>

            <AppCard
                title="Auto Insight"
                subtitle="Temuan otomatis dari analisis terakhir"
            >
                <ul class="space-y-4">
                    <li
                        v-for="insight in insights"
                        :key="insight.title"
                        class="flex gap-3"
                    >
                        <AppIcon
                            :name="insight.tone === 'good' ? 'check' : 'warning'"
                            class="mt-0.5 h-4 w-4 shrink-0"
                            :class="INSIGHT_TONES[insight.tone]"
                        />
                        <div class="min-w-0">
                            <p class="text-sm font-medium text-ink dark:text-ink-dark">
                                {{ insight.title }}
                            </p>
                            <p class="mt-0.5 text-sm text-ink-2 dark:text-ink-2-dark">
                                {{ insight.body }}
                            </p>
                        </div>
                    </li>
                </ul>

                <template #footer>
                    <RouterLink
                        :to="{ name: 'reports.index' }"
                        class="focus-ring rounded text-xs font-medium text-accent hover:underline dark:text-accent-dark"
                    >
                        Buat laporan dari temuan ini
                    </RouterLink>
                </template>
            </AppCard>
        </div>
    </AppLayout>
</template>
