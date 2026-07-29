<script setup>
import { computed, ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import PageHeader from '@/Components/UI/PageHeader.vue';
import StatTile from '@/Components/UI/StatTile.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import StatusBadge from '@/Components/UI/StatusBadge.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useToastStore } from '@/stores/toast';

const datasetStore = useDatasetStore();
const toast = useToastStore();

// STATE UNTUK DATA API (Diawali dengan kosong / null)
const stats = ref([]);
const activityTrend = ref(null);
const jobDistribution = ref(null);
const insights = ref([]);

const isReloading = ref(false);

// FUNGSI UNTUK MENGAMBIL DATA DARI BACKEND
async function fetchDashboardData() {
    isReloading.value = true;

    try {
        // TODO: Ganti ini dengan request Axios ke API Backend Anda
        // const response = await axios.get('/api/dashboard/summary');
        
        // --- SIMULASI API KONDISI AWAL (KOSONG) ---
        const emptyApiResponse = await new Promise((resolve) => setTimeout(() => resolve({
            stats: [
                { label: 'Dataset Aktif', value: '0', icon: 'datasets' },
                { label: 'Analisis Selesai', value: '0', icon: 'check', delta: '-', deltaLabel: 'Belum ada data' },
                { label: 'Model Dilatih', value: '0', icon: 'ml', delta: '-', deltaLabel: 'Belum ada data' },
                { label: 'Laporan Dibuat', value: '0', icon: 'document', delta: '-', deltaLabel: 'Belum ada data' }
            ],
            activityTrend: null, // Null karena belum ada riwayat aktivitas
            jobDistribution: null, // Null karena belum ada job yang dijalankan
            insights: [] // Kosong karena belum ada insight yang bisa ditarik
        }), 1000));
        // -----------------------------------------

        // Update state dengan data dari server (kosong)
        stats.value = emptyApiResponse.stats;
        activityTrend.value = emptyApiResponse.activityTrend;
        jobDistribution.value = emptyApiResponse.jobDistribution;
        insights.value = emptyApiResponse.insights;

    } catch (error) {
        console.error("Gagal memuat dashboard:", error);
        toast.push("Gagal memuat ringkasan dashboard dari server.", "error");
    } finally {
        isReloading.value = false;
    }
}

async function reload() {
    await fetchDashboardData();
    toast.push('Ringkasan dashboard diperbarui.');
}

// Menarik dataset langsung dari store
const recentDatasets = computed(() => datasetStore.items.slice(0, 4));

const DATASET_COLUMNS = [
    { key: 'name', label: 'Nama Dataset' },
    { key: 'rows', label: 'Baris', align: 'right', numeric: true },
    { key: 'columns', label: 'Kolom', align: 'right', numeric: true },
    { key: 'size', label: 'Ukuran', align: 'right', numeric: true },
    { key: 'status', label: 'Status' },
    { key: 'updated_at', label: 'Diperbarui', align: 'right' },
];

const INSIGHT_TONES = {
    good: 'text-[#006300] dark:text-status-good',
    warning: 'text-[#8a5a00] dark:text-status-warning',
    serious: 'text-[#a34418] dark:text-status-serious',
    critical: 'text-status-critical',
};

// TRIGGER FETCH SAAT HALAMAN DIMUAT
onMounted(() => {
    fetchDashboardData();
});
</script>

<template>
    <PageHeader
        title="Dashboard"
        description="Ringkasan dataset, analisis yang berjalan, dan temuan terbaru."
    >
        <template #actions>
            <AppButton icon="refresh" :disabled="isReloading" @click="reload">
                {{ isReloading ? 'Memuat…' : 'Muat Ulang' }}
            </AppButton>
        </template>
    </PageHeader>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <!-- Skeleton Loading saat awal dimuat dan stats masih kosong -->
        <template v-if="!stats.length && isReloading">
            <div v-for="i in 4" :key="i" class="h-24 rounded-xl border border-hairline bg-surface/50 dark:border-hairline-dark dark:bg-surface-dark/50 animate-pulse"></div>
        </template>
        
        <!-- Render Tile Angka 0 jika sudah selesai dimuat -->
        <template v-else>
            <StatTile
                v-for="stat in stats"
                :key="stat.label"
                :label="stat.label"
                :value="stat.value"
                :unit="stat.unit ?? null"
                :icon="stat.icon"
                :delta="stat.delta ?? null"
                :delta-label="stat.deltaLabel"
                :lower-is-better="stat.lowerIsBetter ?? false"
            />
        </template>
    </div>

    <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div class="lg:col-span-2">
            <ChartPanel
                v-if="activityTrend"
                title="Aktivitas Platform"
                subtitle="Tujuh bulan terakhir"
                type="area"
                :labels="activityTrend.labels"
                :series="activityTrend.series"
                :height="280"
            />
            <!-- Tampilkan teks berbeda saat loading vs saat data memang kosong -->
            <div v-else class="flex h-[280px] items-center justify-center rounded-xl border border-hairline bg-surface dark:border-hairline-dark dark:bg-surface-dark">
                <p class="text-sm text-ink-3">
                    {{ isReloading ? 'Memuat grafik...' : 'Belum ada data aktivitas.' }}
                </p>
            </div>
        </div>

        <div>
            <ChartPanel
                v-if="jobDistribution"
                title="Distribusi Job"
                subtitle="Berdasarkan jenis analisis"
                type="doughnut"
                :labels="jobDistribution.labels"
                :series="jobDistribution.series"
                :height="280"
            />
            <!-- Tampilkan teks berbeda saat loading vs saat data memang kosong -->
            <div v-else class="flex h-[280px] items-center justify-center rounded-xl border border-hairline bg-surface dark:border-hairline-dark dark:bg-surface-dark">
                <p class="text-sm text-ink-3">
                    {{ isReloading ? 'Memuat grafik...' : 'Belum ada distribusi job.' }}
                </p>
            </div>
        </div>
    </div>

    <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div class="lg:col-span-2">
            <AppCard title="Dataset Terbaru" flush>
                <template #actions>
                    <RouterLink
                        :to="{ name: 'datasets.index' }"
                        class="focus-ring rounded text-xs font-medium text-accent hover:underline dark:text-accent-dark"
                    >
                        Lihat semua
                    </RouterLink>
                </template>

                <DataTable v-if="recentDatasets.length" :columns="DATASET_COLUMNS" :rows="recentDatasets">
                    <template #cell-name="{ row }">
                        <RouterLink
                            :to="{ name: 'datasets.show', params: { id: row.id } }"
                            class="focus-ring rounded font-medium text-ink hover:text-accent dark:text-ink-dark dark:hover:text-accent-dark"
                        >
                            {{ row.name }}
                        </RouterLink>
                    </template>

                    <template #cell-status="{ row }">
                        <StatusBadge :status="row.status" />
                    </template>
                </DataTable>
                
                <div v-else class="flex flex-col items-center justify-center py-10">
                    <p class="text-sm text-ink-3">Belum ada dataset yang diunggah.</p>
                </div>
            </AppCard>
        </div>

        <AppCard
            title="Auto Insight"
            subtitle="Temuan otomatis dari analisis terakhir"
        >
            <ul v-if="insights.length" class="space-y-4">
                <li
                    v-for="insight in insights"
                    :key="insight.title"
                    class="flex gap-3"
                >
                    <AppIcon
                        :name="insight.tone === 'good' ? 'check' : 'warning'"
                        class="mt-0.5 h-4 w-4 shrink-0"
                        :class="INSIGHT_TONES[insight.tone]"
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
            
            <div v-else class="py-6 text-center">
                <p class="text-sm text-ink-3">Belum ada temuan otomatis.</p>
            </div>

            <template #footer>
                <RouterLink
                    :to="{ name: 'reports.index' }"
                    class="focus-ring rounded text-xs font-medium text-accent hover:underline dark:text-accent-dark"
                >
                    Buka Laporan
                </RouterLink>
            </template>
        </AppCard>
    </div>
</template>