<script setup>
import { ref } from 'vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useToastStore } from '@/stores/toast';
import { cleaning } from '@/data/placeholder';

const { issues, strategies, impact } = cleaning;
const toast = useToastStore();

// Salinan lokal agar pilihan pengguna tidak memutasi data sumber bersama.
const defaultStrategies = () =>
    Object.fromEntries(
        strategies.map((strategy) => [strategy.key, strategy.selected]),
    );

const selectedStrategies = ref(defaultStrategies());
const isApplying = ref(false);

// Simulasi job cleaning; nanti diganti pemanggilan Python engine lewat API.
function applyCleaning() {
    isApplying.value = true;

    setTimeout(() => {
        isApplying.value = false;
        toast.push('Cleaning diterapkan pada salinan dataset — berkas asli utuh.');
    }, 1500);
}

function resetStrategies() {
    selectedStrategies.value = defaultStrategies();
    toast.push('Strategi dikembalikan ke rekomendasi default.', 'info');
}

const ISSUE_TONES = {
    warning: 'text-[#8a5a00] dark:text-status-warning',
    serious: 'text-[#a34418] dark:text-status-serious',
    critical: 'text-status-critical',
};
</script>

<template>
    <PageHeader
        title="Data Cleaning"
        description="Tinjau masalah kualitas data dan tentukan strategi penanganannya sebelum analisis."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Cleaning' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
            <AppButton
                variant="primary"
                icon="play"
                :disabled="isApplying"
                @click="applyCleaning"
            >
                {{ isApplying ? 'Menerapkan…' : 'Terapkan Cleaning' }}
            </AppButton>
        </template>
    </PageHeader>

    <!-- Masalah terdeteksi -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div
            v-for="issue in issues"
            :key="issue.key"
            class="rounded-xl border border-hairline bg-surface p-5 dark:border-hairline-dark dark:bg-surface-dark"
        >
            <div class="flex items-center gap-2">
                <AppIcon
                    :name="issue.icon"
                    class="h-4 w-4 shrink-0"
                    :class="ISSUE_TONES[issue.tone]"
                />
                <p class="text-xs font-medium uppercase tracking-wide text-ink-3">
                    {{ issue.title }}
                </p>
            </div>

            <p class="mt-3 flex items-baseline gap-1.5">
                <span
                    class="text-3xl font-semibold leading-none text-ink dark:text-ink-dark"
                >
                    {{ issue.count.toLocaleString('id-ID') }}
                </span>
                <span class="text-sm text-ink-2 dark:text-ink-2-dark">
                    {{ issue.unit }}
                </span>
            </p>

            <p class="mt-2 text-xs text-ink-2 dark:text-ink-2-dark">
                {{ issue.description }}
            </p>
        </div>
    </div>

    <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div class="lg:col-span-2">
            <AppCard
                title="Strategi Pembersihan"
                subtitle="Pilihan ini menentukan langkah yang dijalankan Python engine."
            >
                <div class="space-y-5">
                    <div
                        v-for="strategy in strategies"
                        :key="strategy.key"
                        class="border-b border-hairline pb-5 last:border-0 last:pb-0 dark:border-hairline-dark"
                    >
                        <p
                            class="mb-2.5 text-sm font-medium text-ink dark:text-ink-dark"
                        >
                            {{ strategy.label }}
                        </p>

                        <div class="flex flex-wrap gap-2">
                            <button
                                v-for="option in strategy.options"
                                :key="option"
                                type="button"
                                class="focus-ring rounded-lg px-3 py-1.5 text-xs font-medium ring-1 ring-inset transition-colors"
                                :class="
                                    selectedStrategies[strategy.key] === option
                                        ? 'bg-accent text-white ring-accent dark:bg-accent-dark dark:ring-accent-dark'
                                        : 'text-ink-2 ring-hairline hover:bg-plane dark:text-ink-2-dark dark:ring-hairline-dark dark:hover:bg-raised-dark'
                                "
                                :aria-pressed="
                                    selectedStrategies[strategy.key] === option
                                "
                                @click="selectedStrategies[strategy.key] = option"
                            >
                                {{ option }}
                            </button>
                        </div>
                    </div>
                </div>

                <template #footer>
                    <div class="flex items-center justify-between gap-3">
                        <p class="text-xs text-ink-3">
                            Perubahan diterapkan pada salinan, dataset asli tetap utuh.
                        </p>
                        <AppButton size="sm" icon="refresh" @click="resetStrategies">
                            Kembalikan Default
                        </AppButton>
                    </div>
                </template>
            </AppCard>
        </div>

        <ChartPanel
            title="Dampak Cleaning"
            subtitle="Perbandingan baris sebelum dan sesudah"
            type="bar"
            stacked
            :labels="impact.labels"
            :series="impact.series"
            :height="300"
        />
    </div>
</template>
