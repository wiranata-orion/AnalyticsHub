<script>
import { reactive } from 'vue';

// Cache global per dataset ID agar data cleaning tersimpan dan tidak loading ulang saat pindah menu
const cleaningCache = reactive({});
</script>

<script setup>
import { ref, watch } from 'vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useToastStore } from '@/stores/toast';

const datasetStore = useDatasetStore();
const toast = useToastStore();

const issues = ref([]);
const strategies = ref([]);
const impact = ref({ labels: [], series: [] });
const selectedStrategies = ref({});

const isLoading = ref(false);
const isApplying = ref(false);

const ISSUE_TONES = {
    warning: 'text-[#8a5a00] dark:text-status-warning',
    serious: 'text-[#a34418] dark:text-status-serious',
    critical: 'text-status-critical',
};

const defaultStrategies = () =>
    Object.fromEntries(
        strategies.value.map((strategy) => [strategy.key, strategy.selected]),
    );

// Ambil data dengan sistem Cache
async function fetchCleaningData(datasetId, force = false) {
    if (!datasetId) return;

    // 1. Cek Cache
    if (!force && cleaningCache[datasetId]) {
        const cached = cleaningCache[datasetId];
        issues.value = cached.issues;
        strategies.value = cached.strategies;
        impact.value = cached.impact;
        selectedStrategies.value = defaultStrategies();
        return;
    }

    isLoading.value = true;
    try {
        // --- SIMULASI API (Lengkap dengan data asli lu) ---
        // Nanti ganti: const response = await axios.get(`/api/datasets/${datasetId}/cleaning-preview`);
        const data = await new Promise((resolve) => setTimeout(() => resolve({
            issues: [
                { key: 'missing', icon: 'warning', tone: 'serious', title: 'Missing Values', count: 1240, unit: 'sel', description: 'Terdapat nilai kosong yang tersebar di beberapa kolom.' },
                { key: 'outlier', icon: 'chart', tone: 'warning', title: 'Outliers', count: 85, unit: 'baris', description: 'Nilai ekstrem terdeteksi pada kolom numerik.' },
                { key: 'duplicate', icon: 'copy', tone: 'warning', title: 'Duplikat', count: 12, unit: 'baris', description: 'Baris data dengan nilai identik persis.' },
                { key: 'type', icon: 'document', tone: 'serious', title: 'Mismatched Types', count: 3, unit: 'kolom', description: 'Tipe data tidak sesuai dengan isi nilainya.' }
            ],
            strategies: [
                { key: 'missing_strat', label: 'Penanganan Missing Values', options: ['Hapus Baris', 'Isi Mean', 'Isi Median', 'Biarkan'], selected: 'Isi Mean' },
                { key: 'outlier_strat', label: 'Penanganan Outliers', options: ['Hapus Baris', 'Cap/Floor', 'Biarkan'], selected: 'Cap/Floor' },
                { key: 'duplicate_strat', label: 'Penanganan Duplikat', options: ['Hapus Duplikat', 'Biarkan'], selected: 'Hapus Duplikat' }
            ],
            impact: {
                labels: ['Sebelum', 'Sesudah'],
                series: [
                    { label: 'Baris Valid', data: [14000, 13748] },
                    { label: 'Baris Bermasalah', data: [1000, 0] }
                ]
            }
        }), 800));
        // -------------------------------------------------

        // 2. Simpan ke Cache
        cleaningCache[datasetId] = data;

        issues.value = data.issues;
        strategies.value = data.strategies;
        impact.value = data.impact;
        
        selectedStrategies.value = defaultStrategies();
    } catch (error) {
        console.error("Gagal mengambil data cleaning:", error);
        toast.push('Gagal mengambil data analisis dari server.', 'error');
    } finally {
        isLoading.value = false;
    }
}

async function applyCleaning() {
    if (!datasetStore.selectedId) return;

    isApplying.value = true;
    try {
        // Simulasi request API POST
        await new Promise(resolve => setTimeout(resolve, 1500));
        toast.push('Cleaning diterapkan pada salinan dataset — berkas asli utuh.');
    } catch (error) {
        console.error("Gagal menerapkan cleaning:", error);
        toast.push('Terjadi kesalahan saat menerapkan cleaning.', 'error');
    } finally {
        isApplying.value = false;
    }
}

function resetStrategies() {
    selectedStrategies.value = defaultStrategies();
    toast.push('Strategi dikembalikan ke rekomendasi default.', 'info');
}

watch(
    () => datasetStore.selectedId,
    (id) => {
        if (id) {
            fetchCleaningData(id);
        } else {
            issues.value = [];
            strategies.value = [];
            impact.value = { labels: [], series: [] };
        }
    },
    { immediate: true },
);
</script>

<template>
    <PageHeader
        title="Data Cleaning"
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
                :disabled="isApplying || isLoading || !datasetStore.selectedId"
                @click="applyCleaning"
            >
                {{ isApplying ? 'Menerapkan…' : 'Terapkan Cleaning' }}
            </AppButton>
        </template>
    </PageHeader>

    <AppCard v-if="!datasetStore.selectedId" flush class="mt-4">
        <EmptyState
            icon="document"
            title="Pilih dataset terlebih dahulu"
            description="Silakan pilih dataset dari menu dropdown di atas untuk memulai data cleaning."
        />
    </AppCard>

    <template v-else>
        <!-- Masalah terdeteksi -->
        <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
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
                        {{ issue.count?.toLocaleString('id-ID') || 0 }}
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
                v-if="impact && impact.labels && impact.labels.length > 0"
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
</template>