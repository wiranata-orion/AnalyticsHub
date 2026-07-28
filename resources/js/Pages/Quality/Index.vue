<script setup>
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import ProgressMeter from '@/Components/UI/ProgressMeter.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useAnalysis } from '@/Composables/useAnalysis';

/*
 * Data Quality Assessment: enam dimensi + skor keseluruhan, dihitung engine
 * Python (python/quality/assessment.py) lewat REST API. Hasil terakhir dimuat
 * otomatis saat halaman dibuka kembali.
 */
const { result, isRunning, isLoading, run, meta } = useAnalysis('quality');

const GRADE_TONES = {
    'Sangat Baik': 'text-[#006300] dark:text-status-good',
    Baik: 'text-[#006300] dark:text-status-good',
    Cukup: 'text-[#8a5a00] dark:text-status-warning',
    Kurang: 'text-[#a34418] dark:text-status-serious',
    Buruk: 'text-status-critical',
};
</script>

<template>
    <PageHeader
        title="Data Quality"
        description="Penilaian kualitas dataset pada enam dimensi: kelengkapan, keunikan, validitas, konsistensi, akurasi, dan ketepatan waktu."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Data Quality' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
            <AppButton variant="primary" icon="play" :disabled="isRunning" @click="run()">
                {{ isRunning ? 'Menilai…' : 'Nilai Kualitas' }}
            </AppButton>
        </template>
    </PageHeader>

    <!-- Saat memuat, kartu ini tidak dirender sama sekali: kartu kosong yang
         muncul lalu langsung hilang lebih mengganggu daripada jeda singkat
         tanpa apa-apa. -->
    <AppCard v-if="!result && !isLoading" flush>
        <EmptyState
            icon="data-quality"
            title="Belum ada penilaian"
            description="Jalankan penilaian untuk menghitung skor kualitas dataset terpilih. Hasilnya tersimpan dan tampil kembali saat halaman dibuka lagi."
        >
            <template #action>
                <AppButton variant="primary" icon="play" :disabled="isRunning" @click="run()">
                    Nilai Kualitas
                </AppButton>
            </template>
        </EmptyState>
    </AppCard>

    <template v-else-if="result">
        <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <AppCard title="Overall Data Quality Score">
                <p class="flex items-baseline gap-2">
                    <span class="text-5xl font-semibold leading-none text-ink dark:text-ink-dark">
                        {{ result.overall_score.toLocaleString('id-ID') }}
                    </span>
                    <span class="text-sm text-ink-3">/ 100</span>
                </p>
                <p class="mt-2 text-sm font-medium" :class="GRADE_TONES[result.grade]">
                    {{ result.grade }}
                </p>
                <p class="mt-3 text-sm text-ink-2 dark:text-ink-2-dark">
                    {{ result.interpretation }}
                </p>

                <template #footer>
                    <p class="text-xs text-ink-3">
                        {{ result.row_count.toLocaleString('id-ID') }} baris ·
                        {{ result.column_count }} kolom
                        <template v-if="meta?.duration_ms"> · dihitung dalam {{ meta.duration_ms }} ms</template>
                    </p>
                </template>
            </AppCard>

            <div class="lg:col-span-2">
                <AppCard title="Skor per Dimensi" subtitle="Dimensi tanpa data pendukung (mis. tanpa kolom waktu) dilewati dari skor.">
                    <div class="space-y-4">
                        <ProgressMeter
                            v-for="dimension in result.dimensions"
                            :key="dimension.key"
                            :label="dimension.label"
                            :value="dimension.score ?? 0"
                            :caption="dimension.score === null ? 'dilewati' : `${dimension.score.toLocaleString('id-ID')} / 100`"
                        />
                    </div>
                </AppCard>
            </div>
        </div>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <AppCard
                v-for="dimension in result.dimensions"
                :key="`detail-${dimension.key}`"
                :title="dimension.label"
                :subtitle="dimension.detail"
            >
                <ul class="space-y-2.5">
                    <li
                        v-for="finding in dimension.findings"
                        :key="finding"
                        class="flex items-start gap-2 text-sm text-ink-2 dark:text-ink-2-dark"
                    >
                        <AppIcon
                            :name="dimension.score === null ? 'warning' : dimension.score >= 90 ? 'check' : 'warning'"
                            class="mt-0.5 h-4 w-4 shrink-0"
                            :class="dimension.score !== null && dimension.score >= 90
                                ? 'text-[#006300] dark:text-status-good'
                                : 'text-[#8a5a00] dark:text-status-warning'"
                        />
                        {{ finding }}
                    </li>
                </ul>
            </AppCard>
        </div>
    </template>
</template>
