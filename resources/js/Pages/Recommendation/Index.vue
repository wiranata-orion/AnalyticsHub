<script setup>
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useAnalysis } from '@/Composables/useAnalysis';

/*
 * Auto Recommendation: sistem membaca karakteristik dataset lalu menyarankan
 * analisis yang sesuai, lengkap dengan alasan yang menyebut kolomnya
 * (python/core/recommender.py). Tiap kartu menautkan ke halaman analisisnya.
 */
const { result, isRunning, isLoading, run } = useAnalysis('recommendation');

const TARGET_PAGES = {
    classification: { route: 'mining.index', label: 'Buka Data Mining' },
    regression: { route: 'mining.index', label: 'Buka Data Mining' },
    clustering: { route: 'mining.index', label: 'Buka Data Mining' },
    association: { route: 'mining.index', label: 'Buka Data Mining' },
    anomaly: { route: 'mining.index', label: 'Buka Data Mining' },
    forecasting: { route: 'forecasting.index', label: 'Buka Forecasting' },
};

const characteristicRows = (c) => [
    { label: 'Baris dianalisis', value: c.row_count.toLocaleString('id-ID') },
    { label: 'Kolom numerik', value: String(c.numeric_count) },
    { label: 'Kolom kategorikal', value: String(c.categorical_count) },
    { label: 'Kolom waktu', value: String(c.datetime_count) },
    { label: 'Nilai ekstrem', value: `${(c.outlier_ratio * 100).toFixed(1).replace('.', ',')}%` },
    { label: 'Bentuk data', value: c.is_transactional ? 'transaksional' : 'tabular biasa' },
    { label: 'Kandidat target', value: c.target_candidates.join(', ') || 'tidak ada' },
];
</script>

<template>
    <PageHeader
        title="Auto Recommendation"
        description="Sistem menganalisis karakteristik dataset lalu menyarankan analisis yang paling sesuai, beserta alasannya."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Auto Recommendation' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
            <AppButton variant="primary" icon="play" :disabled="isRunning" @click="run()">
                {{ isRunning ? 'Menganalisis…' : 'Analisis Dataset' }}
            </AppButton>
        </template>
    </PageHeader>

    <AppCard v-if="!result && !isLoading" flush>
        <EmptyState
            icon="auto-recommendation"
            title="Belum ada rekomendasi"
            description="Jalankan analisis karakteristik untuk mendapatkan saran: klasifikasi bila ada target kategorikal, forecasting bila ada kolom waktu, dan seterusnya."
        >
            <template #action>
                <AppButton variant="primary" icon="play" :disabled="isRunning" @click="run()">
                    Analisis Dataset
                </AppButton>
            </template>
        </EmptyState>
    </AppCard>

    <template v-else-if="result">
        <AppCard
            title="Karakteristik Dataset"
            subtitle="Fakta yang menjadi dasar setiap rekomendasi di bawah."
        >
            <dl class="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-4">
                <div
                    v-for="row in characteristicRows(result.characteristics)"
                    :key="row.label"
                    class="min-w-0"
                >
                    <dt class="text-xs text-ink-3">{{ row.label }}</dt>
                    <dd class="mt-0.5 truncate text-sm font-medium text-ink dark:text-ink-dark" :title="row.value">
                        {{ row.value }}
                    </dd>
                </div>
            </dl>
        </AppCard>

        <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <AppCard
                v-for="item in result.recommendations"
                :key="item.key"
                :title="item.name"
            >
                <template #actions>
                    <AppBadge :variant="item.level === 'high' ? 'good' : 'neutral'">
                        {{ item.level === 'high' ? 'Direkomendasikan' : 'Opsional' }}
                    </AppBadge>
                </template>

                <p class="text-sm text-ink-2 dark:text-ink-2-dark">{{ item.reason }}</p>

                <p v-if="item.suggested_target" class="mt-2 text-xs text-ink-3">
                    Target yang disarankan:
                    <span class="font-medium text-ink dark:text-ink-dark">{{ item.suggested_target }}</span>
                </p>

                <template #footer>
                    <RouterLink
                        :to="{ name: (TARGET_PAGES[item.key] ?? TARGET_PAGES.clustering).route }"
                        class="focus-ring flex items-center gap-1 rounded text-xs font-medium text-accent hover:underline dark:text-accent-dark"
                    >
                        {{ (TARGET_PAGES[item.key] ?? TARGET_PAGES.clustering).label }}
                        <AppIcon name="chevronRight" class="h-3 w-3" />
                    </RouterLink>
                </template>
            </AppCard>
        </div>
    </template>
</template>
