<script setup>
import { computed } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import StatTile from '@/Components/UI/StatTile.vue';
import StatusBadge from '@/Components/UI/StatusBadge.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useToastStore } from '@/stores/toast';
import { downloadCsv } from '@/Utils/exportCsv';

// `id` datang dari parameter rute (`props: true` di definisi rute).
const props = defineProps({
    id: {
        type: [String, Number],
        required: true,
    },
});

const datasetStore = useDatasetStore();
const toast = useToastStore();
const dataset = computed(() => datasetStore.detail(props.id));

function downloadPreview() {
    const baseName = dataset.value.name.replace(/\.[^.]+$/, '');

    downloadCsv(
        `${baseName}_pratinjau.csv`,
        dataset.value.preview.columns,
        dataset.value.preview.rows,
    );
    toast.push('Pratinjau dataset diunduh sebagai CSV.');
}

function showAllRows() {
    toast.push(
        'Seluruh baris baru bisa dibuka setelah backend tersambung — saat ini hanya pratinjau.',
        'warning',
    );
}

const NEXT_STEPS = [
    {
        label: 'Data Profiling',
        icon: 'profiling',
        name: 'profiling.index',
        description: 'Statistik ringkas, missing value, outlier, dan korelasi.',
    },
    {
        label: 'Data Cleaning',
        icon: 'cleaning',
        name: 'cleaning.index',
        description: 'Tangani nilai kosong, duplikat, dan tipe data yang salah.',
    },
    {
        label: 'Visualisasi',
        icon: 'visualization',
        name: 'visualization.index',
        description: 'Bangun grafik distribusi, tren, dan perbandingan.',
    },
    {
        label: 'Data Mining',
        icon: 'mining',
        name: 'mining.index',
        description: 'Clustering, klasifikasi, regresi, dan association rule.',
    },
];
</script>

<template>
    <AppLayout>
        <PageHeader
            :title="dataset.name"
            :breadcrumbs="[
                { label: 'Dashboard', to: { name: 'dashboard' } },
                { label: 'Dataset', to: { name: 'datasets.index' } },
                { label: dataset.name },
            ]"
        >
            <template #actions>
                <AppButton icon="download" @click="downloadPreview">Unduh</AppButton>
                <AppButton
                    variant="primary"
                    icon="play"
                    :to="{ name: 'profiling.index' }"
                >
                    Jalankan Profiling
                </AppButton>
            </template>
        </PageHeader>

        <div class="mb-4 flex flex-wrap items-center gap-2">
            <StatusBadge :status="dataset.status" />
            <AppBadge>{{ dataset.format }}</AppBadge>
            <AppBadge>{{ dataset.encoding }}</AppBadge>
            <span class="text-xs text-ink-3">
                Diunggah {{ dataset.created_at }} oleh {{ dataset.uploaded_by }}
            </span>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile label="Jumlah Baris" :value="dataset.rows" icon="table" />
            <StatTile label="Jumlah Kolom" :value="dataset.columns" icon="datasets" />
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
                    title="Pratinjau Data"
                    :subtitle="`Menampilkan ${dataset.preview.rows.length} baris pertama`"
                    flush
                >
                    <template #actions>
                        <AppButton size="sm" icon="table" @click="showAllRows">
                            Lihat Semua
                        </AppButton>
                    </template>

                    <div class="overflow-x-auto">
                        <table class="w-full text-sm">
                            <thead>
                                <tr class="border-b border-hairline dark:border-hairline-dark">
                                    <th
                                        v-for="(column, index) in dataset.preview.columns"
                                        :key="column"
                                        scope="col"
                                        class="whitespace-nowrap px-4 py-2.5 text-left"
                                    >
                                        <span
                                            class="block text-xs font-medium text-ink dark:text-ink-dark"
                                        >
                                            {{ column }}
                                        </span>
                                        <span
                                            class="mt-0.5 block text-[11px] font-normal lowercase text-ink-3"
                                        >
                                            {{ dataset.preview.types[index] }}
                                        </span>
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr
                                    v-for="(row, rowIndex) in dataset.preview.rows"
                                    :key="rowIndex"
                                    class="border-b border-hairline last:border-0 hover:bg-plane dark:border-hairline-dark dark:hover:bg-raised-dark/60"
                                >
                                    <td
                                        v-for="(cell, cellIndex) in row"
                                        :key="cellIndex"
                                        class="whitespace-nowrap px-4 py-2.5 tabular-nums"
                                        :class="
                                            cell === '—'
                                                ? 'italic text-ink-3'
                                                : 'text-ink-2 dark:text-ink-2-dark'
                                        "
                                    >
                                        {{ cell }}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
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
                            <AppIcon
                                :name="step.icon"
                                class="mt-0.5 h-[18px] w-[18px] shrink-0 text-accent dark:text-accent-dark"
                            />
                            <div class="min-w-0 flex-1">
                                <p class="text-sm font-medium text-ink dark:text-ink-dark">
                                    {{ step.label }}
                                </p>
                                <p class="mt-0.5 text-xs text-ink-2 dark:text-ink-2-dark">
                                    {{ step.description }}
                                </p>
                            </div>
                            <AppIcon
                                name="chevronRight"
                                class="mt-1 h-3.5 w-3.5 shrink-0 text-ink-3"
                            />
                        </RouterLink>
                    </li>
                </ul>
            </AppCard>
        </div>
    </AppLayout>
</template>
