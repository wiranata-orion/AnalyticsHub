<script setup>
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useAnalysis } from '@/Composables/useAnalysis';

/*
 * Auto Insight: temuan otomatis dalam kalimat, dihasilkan engine Python
 * (python/insight/generator.py). Tiap temuan membawa judul, penjelasan, dan
 * nada — halaman tinggal menampilkannya.
 */
const { result, isRunning, isLoading, run, meta } = useAnalysis('insight');

const TONES = {
    good: { icon: 'check', class: 'text-[#006300] dark:text-status-good' },
    info: { icon: 'auto-insight', class: 'text-accent dark:text-accent-dark' },
    warning: { icon: 'warning', class: 'text-[#8a5a00] dark:text-status-warning' },
    serious: { icon: 'warning', class: 'text-[#a34418] dark:text-status-serious' },
};
</script>

<template>
    <PageHeader
        title="Auto Insight"
        description="Temuan otomatis dari dataset terpilih — bukan hanya angka, tetapi penjelasan singkat yang bisa langsung ditindaklanjuti."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Auto Insight' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
            <AppButton variant="primary" icon="play" :disabled="isRunning" @click="run()">
                {{ isRunning ? 'Menganalisis…' : 'Hasilkan Insight' }}
            </AppButton>
        </template>
    </PageHeader>

    <!-- Tidak dirender saat memuat; lihat catatan di halaman Data Quality. -->
    <AppCard v-if="!result && !isLoading" flush>
        <EmptyState
            icon="auto-insight"
            title="Belum ada insight"
            description="Jalankan analisis untuk menghasilkan temuan otomatis: missing value yang menonjol, korelasi kuat, ketidakseimbangan kelas, nilai ekstrem, dan arah tren."
        >
            <template #action>
                <AppButton variant="primary" icon="play" :disabled="isRunning" @click="run()">
                    Hasilkan Insight
                </AppButton>
            </template>
        </EmptyState>
    </AppCard>

    <AppCard
        v-else-if="result"
        title="Temuan"
        :subtitle="`${result.insights.length} temuan dari ${result.row_count.toLocaleString('id-ID')} baris` +
            (meta?.ran_at ? ` · dianalisis ${new Date(meta.ran_at).toLocaleString('id-ID')}` : '')"
    >
        <ul class="space-y-5">
            <li v-for="insight in result.insights" :key="insight.title" class="flex gap-3">
                <AppIcon
                    :name="(TONES[insight.tone] ?? TONES.info).icon"
                    class="mt-0.5 h-4 w-4 shrink-0"
                    :class="(TONES[insight.tone] ?? TONES.info).class"
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
    </AppCard>
</template>
