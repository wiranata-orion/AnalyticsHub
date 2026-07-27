<script setup>
import { computed } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import StatusBadge from '@/Components/UI/StatusBadge.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { sequentialAt } from '@/Utils/palette';
import { machineLearning } from '@/data/placeholder';

const {
    models,
    featureImportance,
    learningCurve,
    confusionMatrix,
    evaluation,
} = machineLearning;

const MODEL_COLUMNS = [
    { key: 'name', label: 'Nama Model' },
    { key: 'algorithm', label: 'Algoritma' },
    { key: 'target', label: 'Target' },
    { key: 'metric', label: 'Metrik' },
    { key: 'score', label: 'Skor', align: 'right', numeric: true },
    { key: 'status', label: 'Status' },
    { key: 'trained_at', label: 'Dilatih', align: 'right' },
];

/*
 * Confusion matrix memakai skala SEKUENSIAL satu rona: nilainya adalah jumlah
 * (besaran tanpa polaritas), bukan selisih dua arah. Angka tetap dicetak di
 * setiap sel, jadi warna hanya membantu memindai.
 */
const matrixMax = computed(() => Math.max(...confusionMatrix.matrix.flat()));

const matrixCells = computed(() =>
    confusionMatrix.matrix.map((row) =>
        row.map((value) => {
            const ratio = value / matrixMax.value;

            return {
                value,
                background: sequentialAt(ratio),
                color: ratio > 0.55 ? '#ffffff' : '#0b0b0b',
            };
        }),
    ),
);
</script>

<template>
    <AppLayout>
        <PageHeader
            title="Machine Learning"
            description="Latih, evaluasi, dan bandingkan model prediktif dari dataset yang sudah dibersihkan."
            :breadcrumbs="[
                { label: 'Dashboard', to: { name: 'dashboard' } },
                { label: 'Machine Learning' },
            ]"
        >
            <template #actions>
                <DatasetSelector />
                <AppButton variant="primary" icon="plus">Latih Model</AppButton>
            </template>
        </PageHeader>

        <AppCard title="Model Tersimpan" flush>
            <DataTable :columns="MODEL_COLUMNS" :rows="models">
                <template #cell-name="{ row }">
                    <span class="font-medium text-ink dark:text-ink-dark">
                        {{ row.name }}
                    </span>
                </template>

                <template #cell-score="{ row }">
                    <span class="font-medium text-ink dark:text-ink-dark">
                        {{ row.score }}
                    </span>
                </template>

                <template #cell-status="{ row }">
                    <StatusBadge :status="row.status" />
                </template>
            </DataTable>
        </AppCard>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChartPanel
                title="Feature Importance"
                subtitle="Kontribusi tiap fitur pada model churn"
                type="bar"
                horizontal
                :labels="featureImportance.labels"
                :series="featureImportance.series"
                :height="280"
            />

            <ChartPanel
                title="Learning Curve"
                subtitle="Akurasi terhadap proporsi data latih"
                type="line"
                :labels="learningCurve.labels"
                :series="learningCurve.series"
                :height="280"
            />
        </div>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <AppCard
                title="Confusion Matrix"
                subtitle="Prediksi model churn pada data uji"
            >
                <div class="overflow-x-auto">
                    <table class="border-separate border-spacing-1 text-sm">
                        <thead>
                            <tr>
                                <th class="p-1" />
                                <th
                                    :colspan="confusionMatrix.labels.length"
                                    class="pb-1 text-center text-xs font-medium text-ink-3"
                                >
                                    Prediksi
                                </th>
                            </tr>
                            <tr>
                                <th class="p-1" />
                                <th
                                    v-for="label in confusionMatrix.labels"
                                    :key="label"
                                    class="px-2 pb-1 text-center text-xs font-medium text-ink-2 dark:text-ink-2-dark"
                                >
                                    {{ label }}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr
                                v-for="(row, rowIndex) in matrixCells"
                                :key="rowIndex"
                            >
                                <th
                                    class="whitespace-nowrap pr-2 text-right text-xs font-medium text-ink-2 dark:text-ink-2-dark"
                                >
                                    {{ confusionMatrix.labels[rowIndex] }}
                                </th>
                                <td
                                    v-for="(cell, colIndex) in row"
                                    :key="colIndex"
                                    class="h-14 min-w-[5rem] rounded-lg text-center font-medium tabular-nums"
                                    :style="{
                                        backgroundColor: cell.background,
                                        color: cell.color,
                                    }"
                                >
                                    {{ cell.value.toLocaleString('id-ID') }}
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <p class="mt-3 text-xs text-ink-3">
                    Diagonal utama adalah prediksi benar. Baris = kelas sebenarnya.
                </p>
            </AppCard>

            <div class="lg:col-span-2">
                <AppCard title="Ringkasan Evaluasi">
                    <div class="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-4">
                        <div
                            v-for="metric in evaluation"
                            :key="metric.label"
                        >
                            <p class="text-xs font-medium uppercase tracking-wide text-ink-3">
                                {{ metric.label }}
                            </p>
                            <p
                                class="mt-1.5 text-xl font-semibold text-ink dark:text-ink-dark"
                            >
                                {{ metric.value }}
                            </p>
                        </div>
                    </div>

                    <template #footer>
                        <div class="flex items-center gap-2">
                            <AppIcon
                                name="check"
                                class="h-4 w-4 shrink-0 text-[#006300] dark:text-status-good"
                            />
                            <p class="text-xs text-ink-2 dark:text-ink-2-dark">
                                Model lolos ambang minimum akurasi 85% dan siap dipakai.
                            </p>
                        </div>
                    </template>
                </AppCard>
            </div>
        </div>
    </AppLayout>
</template>
