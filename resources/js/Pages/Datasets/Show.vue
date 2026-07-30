<script setup>
import { onMounted, ref, watch } from 'vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import StatTile from '@/Components/UI/StatTile.vue';
import StatusBadge from '@/Components/UI/StatusBadge.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useToastStore } from '@/stores/toast';
import { api } from '@/Utils/api';
import { formatNumber } from '@/Utils/profiler';

/*
 * Detail dataset dari REST API: metadata berkas + profil per kolom hasil
 * engine Python. "Profiling Ulang" membaca ulang berkas dari storage — dipakai
 * bila profiling pertama gagal atau berkasnya diganti manual.
 */
const props = defineProps({
    id: {
        type: [String, Number],
        required: true,
    },
});

const datasetStore = useDatasetStore();
const toast = useToastStore();

const dataset = ref(null);
const isReprofiling = ref(false);

async function load() {
    dataset.value = null;

    try {
        dataset.value = await datasetStore.fetchDetail(props.id);
    } catch (error) {
        toast.push(error.message, 'warning');
    }
}

onMounted(load);
watch(() => props.id, load);

async function reprofile() {
    isReprofiling.value = true;

    try {
        const response = await api.datasets.reprofile(props.id);

        dataset.value = response.data;
        datasetStore.details[Number(props.id)] = response.data;
        toast.push('Profiling ulang selesai.');
    } catch (error) {
        toast.push(error.message, 'warning');
    } finally {
        isReprofiling.value = false;
    }
}

const COLUMN_TABLE = [
    { key: 'name', label: 'Kolom' },
    { key: 'type', label: 'Tipe' },
    { key: 'missing', label: 'Missing', align: 'right', numeric: true },
    { key: 'unique', label: 'Unik', align: 'right', numeric: true },
    { key: 'mean', label: 'Mean', align: 'right', numeric: true },
    { key: 'median', label: 'Median', align: 'right', numeric: true },
    { key: 'min', label: 'Min', align: 'right', numeric: true },
    { key: 'max', label: 'Maks', align: 'right', numeric: true },
    { key: 'outlier_count', label: 'Outlier', align: 'right', numeric: true },
];

const NEXT_STEPS = [
    { label: 'Data Profiling', icon: 'profiling', name: 'profiling.index', description: 'Statistik ringkas, missing value, outlier, dan korelasi.' },
    { label: 'EDA', icon: 'eda', name: 'eda.index', description: 'Sebaran, hubungan antar kolom, dan pola kekosongan.' },
    { label: 'Auto Recommendation', icon: 'auto-recommendation', name: 'auto-recommendation.index', description: 'Saran analisis yang sesuai karakteristik dataset ini.' },
    { label: 'Data Mining', icon: 'mining', name: 'mining.index', description: 'Clustering, klasifikasi, regresi, dan association rule.' },
];

const fmt = (value) => (value === null || value === undefined ? '—' : formatNumber(Number(value)));
</script>

<template>
    <template v-if="dataset">
        <PageHeader
            :title="dataset.name"
            :breadcrumbs="[
                { label: 'Dashboard', to: { name: 'dashboard' } },
                { label: 'Dataset', to: { name: 'datasets.index' } },
                { label: dataset.name },
            ]"
        >
            <template #actions>
                <AppButton variant="primary" icon="play"  :disabled="isReprofiling" @click="reprofile">
                    {{ isReprofiling ? 'Memproses…' : 'Profiling Ulang' }}
                </AppButton>
            </template>
        </PageHeader>

        <div class="mb-4 flex flex-wrap items-center gap-2">
            <StatusBadge :status="dataset.status" />
            <AppBadge>{{ dataset.format }}</AppBadge>
            <AppBadge>{{ dataset.encoding }}</AppBadge>
            <span class="text-xs text-ink-3">Diunggah {{ dataset.created_at }}</span>
        </div>

        <p
            v-if="dataset.error_message"
            class="mb-4 flex items-start gap-2 rounded-xl border border-hairline bg-surface p-4 text-sm text-ink-2 dark:border-hairline-dark dark:bg-surface-dark dark:text-ink-2-dark"
        >
            <AppIcon name="warning" class="mt-0.5 h-4 w-4 shrink-0 text-status-critical" />
            {{ dataset.error_message }}
        </p>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile label="Jumlah Baris" :value="dataset.rows?.toLocaleString('id-ID') ?? '—'" icon="table" />
            <StatTile label="Jumlah Kolom" :value="dataset.columns_count ?? '—'" icon="datasets" />
            <StatTile label="Ukuran Berkas" :value="dataset.size" icon="document" />
            <StatTile
                label="Pemisah Kolom"
                :value="dataset.delimiter === ',' ? 'Koma' : dataset.delimiter"
                icon="settings"
            />
        </div>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div class="lg:col-span-2">
                <AppCard
                    title="Profil Kolom"
                    subtitle="Dihitung engine Python saat berkas diunggah."
                    flush
                >
                    <DataTable :columns="COLUMN_TABLE" :rows="dataset.columns" row-key="name">
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
                        <template v-for="key in ['mean', 'median', 'min', 'max']" #[`cell-${key}`]="{ row }" :key="key">
                            {{ fmt(row[key]) }}
                        </template>
                        <template #cell-outlier_count="{ row }">
                            <span :class="row.outlier_count > 0 ? 'text-ink dark:text-ink-dark' : 'text-ink-3'">
                                {{ row.outlier_count.toLocaleString('id-ID') }}
                            </span>
                        </template>
                    </DataTable>
                </AppCard>
            </div>

            <AppCard title="Langkah Berikutnya" flush>
                <ul>
                    <li
                        v-for="step in NEXT_STEPS"
                        :key="step.label"
                        class="border-b border-hairline last:border-0 dark:border-hairline-dark"
                    >
                        <RouterLink
                            :to="{ name: step.name }"
                            class="focus-ring flex gap-3 px-5 py-3.5 transition-colors hover:bg-plane dark:hover:bg-raised-dark/60"
                        >
                            <AppIcon :name="step.icon" class="mt-0.5 h-[18px] w-[18px] shrink-0 text-accent dark:text-accent-dark" />
                            <div class="min-w-0 flex-1">
                                <p class="text-sm font-medium text-ink dark:text-ink-dark">{{ step.label }}</p>
                                <p class="mt-0.5 text-xs text-ink-2 dark:text-ink-2-dark">{{ step.description }}</p>
                            </div>
                            <AppIcon name="chevronRight" class="mt-1 h-3.5 w-3.5 shrink-0 text-ink-3" />
                        </RouterLink>
                    </li>
                </ul>
            </AppCard>
        </div>
    </template>

    <AppCard v-else flush>
        <EmptyState icon="datasets" title="Memuat detail dataset…" description="Mengambil metadata dan profil kolom dari server." />
    </AppCard>
</template>
