<script setup>
import { ref, onMounted } from 'vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useToastStore } from '@/stores/toast';

const toast = useToastStore();

// State reaktif dengan nilai awal kosong (aman untuk di-render langsung)
const issues = ref([]);
const strategies = ref([]);
const impact = ref({ labels: [], series: [] });
const selectedStrategies = ref({});

// Status proses API
const isLoading = ref(true); // Tetap dipertahankan HANYA untuk menonaktifkan tombol Terapkan
const isApplying = ref(false);

const ISSUE_TONES = {
    warning: 'text-[#8a5a00] dark:text-status-warning',
    serious: 'text-[#a34418] dark:text-status-serious',
    critical: 'text-status-critical',
};

// Fungsi untuk membentuk default state berdasarkan data dari backend
const generateDefaultStrategies = () => {
    return Object.fromEntries(
        strategies.value.map((strategy) => [strategy.key, strategy.selected]),
    );
};

// Ambil data dari Backend
async function fetchCleaningData() {
    isLoading.value = true;
    try {
        // --- SIMULASI PEMANGGILAN API ---
        const fakeApiResponse = await new Promise((resolve) => setTimeout(() => resolve({
            issues: [ /* Data dari python */ ],
            strategies: [ /* Data dari python */ ],
            impact: { labels: [], series: [] }
        }), 1000));
        // --------------------------------

        // Setel data
        // issues.value = response.data.issues;
        // strategies.value = response.data.strategies;
        // impact.value = response.data.impact;
        
        selectedStrategies.value = generateDefaultStrategies();
    } catch (error) {
        console.error("Gagal mengambil data cleaning:", error);
        toast.push('Gagal mengambil data analisis dari server.', 'error');
    } finally {
        isLoading.value = false;
    }
}

// Kirim data ke Backend
async function applyCleaning() {
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
    selectedStrategies.value = generateDefaultStrategies();
    toast.push('Strategi dikembalikan ke rekomendasi default.', 'info');
}

onMounted(() => {
    fetchCleaningData();
});
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
            <!-- Tombol tetap di-disable jika sedang ambil data awal atau sedang apply -->
            <AppButton
                variant="primary"
                icon="play"
                :disabled="isApplying || isLoading"
                @click="applyCleaning"
            >
                {{ isApplying ? 'Menerapkan…' : 'Terapkan Cleaning' }}
            </AppButton>
        </template>
    </PageHeader>

    <!-- LANGSUNG RENDER KONTEN (Tanpa v-if="isLoading" atau v-else) -->
    
    <!-- Masalah terdeteksi -->
    <!-- Jika 'issues' masih kosong saat awal, div ini tidak akan error, hanya tidak merender apa-apa dulu -->
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
                <!-- Jika 'strategies' kosong, div di bawah ini aman (kosong sementara) -->
                <div class="space-y-5">
                    <div
                        v-for="strategy in strategies"
                        :key="strategy.key"
                        class="border-b border-hairline pb-5 last:border-0 last:pb-0 dark:border-hairline-dark"
                    >
                        <p class="mb-2.5 text-sm font-medium text-ink dark:text-ink-dark">
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
                                :aria-pressed="selectedStrategies[strategy.key] === option"
                                @click="selectedStrategies[strategy.key] = option"
                            >
                                {{ option }}
                            </button>
                        </div>
                    </div>
                    
                    <!-- Pesan sementara jika strategi belum dimuat (opsional) -->
                    <p v-if="strategies.length === 0" class="text-sm text-ink-3">
                        Menunggu rekomendasi strategi dari server...
                    </p>
                </div>

                <template #footer>
                    <div class="flex items-center justify-between gap-3">
                        <p class="text-xs text-ink-3">
                            Perubahan diterapkan pada salinan, dataset asli tetap utuh.
                        </p>
                        <AppButton size="sm" icon="refresh" :disabled="isLoading" @click="resetStrategies">
                            Kembalikan Default
                        </AppButton>
                    </div>
                </template>
            </AppCard>
        </div>

        <!-- Render Chart hanya jika label/series sudah terisi dari API -->
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
        <!-- Tempat penampung kosong yang aman saat grafik belum datang -->
        <div v-else class="flex h-[300px] items-center justify-center rounded-xl border border-hairline dark:border-hairline-dark bg-surface dark:bg-surface-dark">
            <p class="text-sm text-ink-3">Data grafik belum tersedia</p>
        </div>
    </div>
</template> 