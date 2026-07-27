<script setup>
import { ref } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { mining } from '@/data/placeholder';

const { algorithms, clusterPreview, associationRules } = mining;
const selectedAlgorithm = ref('clustering');

const RULE_COLUMNS = [
    { key: 'antecedent', label: 'Jika Membeli' },
    { key: 'consequent', label: 'Maka Membeli' },
    { key: 'support', label: 'Support', align: 'right', numeric: true },
    { key: 'confidence', label: 'Confidence', align: 'right', numeric: true },
    { key: 'lift', label: 'Lift', align: 'right', numeric: true },
];
</script>

<template>
    <AppLayout>
        <PageHeader
            title="Data Mining"
            description="Pilih algoritma, tentukan parameter, dan jalankan pada dataset terpilih."
            :breadcrumbs="[
                { label: 'Dashboard', to: { name: 'dashboard' } },
                { label: 'Data Mining' },
            ]"
        >
            <template #actions>
                <DatasetSelector />
                <AppButton variant="primary" icon="play">
                    Jalankan Analisis
                </AppButton>
            </template>
        </PageHeader>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <button
                v-for="algorithm in algorithms"
                :key="algorithm.key"
                type="button"
                class="focus-ring rounded-xl border bg-surface p-5 text-left transition-colors dark:bg-surface-dark"
                :class="
                    selectedAlgorithm === algorithm.key
                        ? 'border-accent ring-1 ring-accent dark:border-accent-dark dark:ring-accent-dark'
                        : 'border-hairline hover:bg-plane dark:border-hairline-dark dark:hover:bg-raised-dark/60'
                "
                :aria-pressed="selectedAlgorithm === algorithm.key"
                @click="selectedAlgorithm = algorithm.key"
            >
                <div class="flex items-start justify-between gap-3">
                    <span
                        class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-plane text-accent dark:bg-raised-dark dark:text-accent-dark"
                    >
                        <AppIcon :name="algorithm.icon" class="h-[18px] w-[18px]" />
                    </span>

                    <AppIcon
                        v-if="selectedAlgorithm === algorithm.key"
                        name="check"
                        class="h-4 w-4 shrink-0 text-accent dark:text-accent-dark"
                    />
                </div>

                <p class="mt-3.5 text-sm font-medium text-ink dark:text-ink-dark">
                    {{ algorithm.name }}
                </p>
                <p class="mt-1 text-sm text-ink-2 dark:text-ink-2-dark">
                    {{ algorithm.description }}
                </p>
                <p class="mt-3 text-xs tabular-nums text-ink-3">
                    {{ algorithm.runs }} kali dijalankan
                </p>
            </button>
        </div>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChartPanel
                title="Hasil Clustering Terakhir"
                subtitle="K-Means, k = 3, diproyeksikan ke dua komponen utama"
                type="scatter"
                :series="clusterPreview.series"
                :height="300"
            />

            <AppCard
                title="Parameter Algoritma"
                subtitle="Nilai default mengikuti rekomendasi profiling."
            >
                <div class="space-y-4">
                    <div>
                        <label
                            class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark"
                        >
                            Jumlah Cluster (k)
                        </label>
                        <input
                            type="number"
                            value="3"
                            min="2"
                            max="20"
                            class="focus-ring h-9 w-full rounded-lg border-hairline bg-plane text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                        />
                    </div>

                    <div>
                        <label
                            class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark"
                        >
                            Metode Inisialisasi
                        </label>
                        <select
                            class="focus-ring h-9 w-full rounded-lg border-hairline bg-plane py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                        >
                            <option>k-means++</option>
                            <option>random</option>
                        </select>
                    </div>

                    <div>
                        <label
                            class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark"
                        >
                            Maksimum Iterasi
                        </label>
                        <input
                            type="number"
                            value="300"
                            class="focus-ring h-9 w-full rounded-lg border-hairline bg-plane text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                        />
                    </div>

                    <label class="flex items-center gap-2.5 pt-1">
                        <input
                            type="checkbox"
                            checked
                            class="focus-ring h-4 w-4 rounded border-hairline text-accent focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark"
                        />
                        <span class="text-sm text-ink-2 dark:text-ink-2-dark">
                            Standardisasi fitur sebelum training
                        </span>
                    </label>
                </div>
            </AppCard>
        </div>

        <AppCard class="mt-4" title="Association Rule" subtitle="Aturan dengan lift tertinggi" flush>
            <template #actions>
                <AppButton size="sm" icon="download">Ekspor</AppButton>
            </template>

            <DataTable :columns="RULE_COLUMNS" :rows="associationRules">
                <template #cell-antecedent="{ row }">
                    <span class="font-medium text-ink dark:text-ink-dark">
                        {{ row.antecedent }}
                    </span>
                </template>

                <template #cell-consequent="{ row }">
                    <span class="flex items-center gap-1.5">
                        <AppIcon
                            name="chevronRight"
                            class="h-3 w-3 shrink-0 text-ink-3"
                        />
                        <span class="font-medium text-ink dark:text-ink-dark">
                            {{ row.consequent }}
                        </span>
                    </span>
                </template>
            </DataTable>
        </AppCard>
    </AppLayout>
</template>
