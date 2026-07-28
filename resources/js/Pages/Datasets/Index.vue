<script setup>
import { computed, ref } from 'vue';
import { RouterLink } from 'vue-router';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import StatusBadge from '@/Components/UI/StatusBadge.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useToastStore } from '@/stores/toast';
import { useConfirmStore } from '@/stores/confirm';

/*
 * Daftar dataset dari REST API. Berkas yang tampil di sini benar-benar
 * tersimpan di server dan sudah diprofiling engine Python.
 */
const datasetStore = useDatasetStore();
const toast = useToastStore();
const confirm = useConfirmStore();

const search = ref('');
const statusFilter = ref('all');

const STATUS_FILTERS = [
    { value: 'all', label: 'Semua' },
    { value: 'ready', label: 'Siap' },
    { value: 'profiling', label: 'Diproses' },
    { value: 'failed', label: 'Gagal' },
];

const COLUMNS = [
    { key: 'name', label: 'Nama Dataset' },
    { key: 'format', label: 'Format' },
    { key: 'rows', label: 'Baris', align: 'right', numeric: true },
    { key: 'columns', label: 'Kolom', align: 'right', numeric: true },
    { key: 'size', label: 'Ukuran', align: 'right', numeric: true },
    { key: 'status', label: 'Status' },
    { key: 'created_at', label: 'Diunggah', align: 'right' },
    { key: 'actions', label: '', align: 'right', width: '1%' },
];

const filtered = computed(() =>
    datasetStore.items.filter((dataset) => {
        const matchesSearch = dataset.name
            .toLowerCase()
            .includes(search.value.toLowerCase());
        const matchesStatus =
            statusFilter.value === 'all' || dataset.status === statusFilter.value;

        return matchesSearch && matchesStatus;
    }),
);

function resetFilters() {
    search.value = '';
    statusFilter.value = 'all';
}

async function removeDataset(dataset) {
    const approved = await confirm.open({
        title: 'Hapus dataset',
        message: `"${dataset.name}" beserta seluruh hasil analisis, feature set, dan modelnya akan dihapus dari server.`,
    });

    if (!approved) {
        return;
    }

    try {
        await datasetStore.remove(dataset.id);
        toast.push(`Dataset "${dataset.name}" dihapus.`);
    } catch (error) {
        toast.push(error.message, 'warning');
    }
}
</script>

<template>
    <PageHeader
        title="Dataset"
        description="Kelola berkas yang sudah diunggah dan lanjutkan ke tahap analisis."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Dataset' },
        ]"
    >
        <template #actions>
            <AppButton icon="refresh" :disabled="datasetStore.isLoading" @click="datasetStore.fetchAll()">
                Muat Ulang
            </AppButton>
            <AppButton variant="primary" icon="upload" :to="{ name: 'datasets.create' }">
                Upload Dataset
            </AppButton>
        </template>
    </PageHeader>

    <AppCard flush>
        <div class="flex flex-wrap items-center gap-3 border-b border-hairline px-5 py-3 dark:border-hairline-dark">
            <div class="relative min-w-0 flex-1 sm:max-w-xs">
                <AppIcon
                    name="search"
                    class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3"
                />
                <input
                    v-model="search"
                    type="search"
                    placeholder="Cari nama dataset…"
                    class="focus-ring h-9 w-full rounded-lg border-hairline bg-plane pl-9 pr-3 text-sm text-ink placeholder:text-ink-3 focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                />
            </div>

            <div
                class="flex items-center gap-0.5 rounded-lg border border-hairline p-0.5 dark:border-hairline-dark"
                role="group"
                aria-label="Saring status"
            >
                <button
                    v-for="filter in STATUS_FILTERS"
                    :key="filter.value"
                    type="button"
                    class="focus-ring rounded-md px-2.5 py-1 text-xs font-medium transition-colors"
                    :class="statusFilter === filter.value
                        ? 'bg-plane text-ink dark:bg-raised-dark dark:text-ink-dark'
                        : 'text-ink-3 hover:text-ink dark:hover:text-ink-dark'"
                    :aria-pressed="statusFilter === filter.value"
                    @click="statusFilter = filter.value"
                >
                    {{ filter.label }}
                </button>
            </div>

            <p class="ml-auto text-xs tabular-nums text-ink-3">
                {{ filtered.length }} dari {{ datasetStore.items.length }} dataset
            </p>
        </div>

        <DataTable v-if="filtered.length" :columns="COLUMNS" :rows="filtered">
            <template #cell-name="{ row }">
                <RouterLink
                    :to="{ name: 'datasets.show', params: { id: row.id } }"
                    class="focus-ring flex items-center gap-2 rounded font-medium text-ink hover:text-accent dark:text-ink-dark dark:hover:text-accent-dark"
                >
                    <AppIcon name="document" class="h-4 w-4 shrink-0 text-ink-3" />
                    {{ row.name }}
                </RouterLink>
            </template>

            <template #cell-rows="{ row }">
                {{ row.rows?.toLocaleString('id-ID') ?? '—' }}
            </template>

            <template #cell-status="{ row }">
                <StatusBadge :status="row.status" />
            </template>

            <template #cell-actions="{ row }">
                <div class="flex items-center justify-end gap-1">
                    <RouterLink
                        :to="{ name: 'datasets.show', params: { id: row.id } }"
                        class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-ink dark:hover:text-ink-dark"
                        title="Lihat detail"
                    >
                        <AppIcon name="eye" class="h-4 w-4" />
                    </RouterLink>
                    <button
                        type="button"
                        class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-status-critical"
                        title="Hapus dataset"
                        @click="removeDataset(row)"
                    >
                        <AppIcon name="trash" class="h-4 w-4" />
                        <span class="sr-only">Hapus {{ row.name }}</span>
                    </button>
                </div>
            </template>
        </DataTable>

        <EmptyState
            v-else-if="datasetStore.items.length === 0 && !datasetStore.isLoading"
            icon="datasets"
            title="Belum ada dataset"
            :description="datasetStore.loadError
                ? datasetStore.loadError
                : 'Unggah berkas CSV atau Excel — profiling berjalan otomatis begitu unggahan selesai.'"
        >
            <template #action>
                <AppButton variant="primary" icon="upload" :to="{ name: 'datasets.create' }">
                    Upload Dataset
                </AppButton>
            </template>
        </EmptyState>

        <EmptyState
            v-else
            icon="search"
            title="Dataset tidak ditemukan"
            description="Tidak ada dataset yang cocok dengan pencarian atau filter saat ini."
        >
            <template #action>
                <AppButton icon="refresh" @click="resetFilters">Reset Filter</AppButton>
            </template>
        </EmptyState>
    </AppCard>
</template>
