<script>
import { reactive } from 'vue';

// 1. STATE GLOBAL (CACHE)
// Variabel ini hidup di luar siklus komponen. Jika Anda pindah halaman lalu kembali, 
// data ini tidak akan terhapus dan bisa langsung ditampilkan tanpa loading ulang.
const dashboardCache = reactive({
    stats: [],
    activityTrend: null,
    jobDistribution: null,
    insights: [],
    isLoaded: false // Penanda apakah API sudah pernah dipanggil
});
</script>

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

const isReloading = ref(false);

// 2. FUNGSI FETCH DENGAN SISTEM CACHE
// Kita tambahkan parameter 'force' untuk memaksa pengambilan ulang saat tombol diklik
async function fetchDashboardData(force = false) {
    // Jika data sudah ada di memori dan tidak dipaksa muat ulang, batalkan request API!
    if (dashboardCache.isLoaded && !force) {
        return; 
    }

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
            activityTrend: null, 
            jobDistribution: null, 
            insights: [] 
        }), 1000));
        // -----------------------------------------

        // 3. SIMPAN DATA KE DALAM CACHE
        dashboardCache.stats = emptyApiResponse.stats;
        dashboardCache.activityTrend = emptyApiResponse.activityTrend;
        dashboardCache.jobDistribution = emptyApiResponse.jobDistribution;
        dashboardCache.insights = emptyApiResponse.insights;
        
        // Tandai bahwa cache sudah terisi
        dashboardCache.isLoaded = true;

    } catch (error) {
        console.error("Gagal memuat dashboard:", error);
        toast.push("Gagal memuat ringkasan dashboard dari server.", "error");
    } finally {
        isReloading.value = false;
    }
}

// Fungsi reload dipanggil dari tombol, parameter 'true' berarti paksa muat ulang!
async function reload() {
    await fetchDashboardData(true);
    toast.push('Ringkasan dashboard diperbarui.');
}

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
    >
        <template #actions>
            <AppButton icon="refresh" :disabled="isReloading" @click="reload">
                {{ isReloading ? 'Memuat…' : 'Muat Ulang' }}
            </AppButton>
        </template>
    </PageHeader>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <!-- Pengecekan membaca dari dashboardCache -->
        <template v-if="!dashboardCache.stats.length && isReloading">
            <div v-for="i in 4" :key="i" class="h-24 rounded-xl border border-hairline bg-surface/50 dark:border-hairline-dark dark:bg-surface-dark/50 animate-pulse"></div>
        </template>
        
        <template v-else>
            <StatTile
                v-for="stat in dashboardCache.stats"
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
                v-if="dashboardCache.activityTrend"
                title="Aktivitas Platform"
                subtitle="Tujuh bulan terakhir"
                type="area"
                :labels="dashboardCache.activityTrend.labels"
                :series="dashboardCache.activityTrend.series"
                :height="280"
            />
            <div v-else class="flex h-[280px] items-center justify-center rounded-xl border border-hairline bg-surface dark:border-hairline-dark dark:bg-surface-dark">
                <p class="text-sm text-ink-3">
                    {{ isReloading ? 'Memuat grafik...' : 'Belum ada data aktivitas.' }}
                </p>
            </div>
        </div>

        <div>
            <ChartPanel
                v-if="dashboardCache.jobDistribution"
                title="Distribusi Job"
                subtitle="Berdasarkan jenis analisis"
                type="doughnut"
                :labels="dashboardCache.jobDistribution.labels"
                :series="dashboardCache.jobDistribution.series"
                :height="280"
            />
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
            <ul v-if="dashboardCache.insights.length" class="space-y-4">
                <li
                    v-for="insight in dashboardCache.insights"
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