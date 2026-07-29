<script>
import { reactive } from 'vue';

// Cache global per dataset ID agar pilihan algoritma dan hasil analisis tidak hilang saat pindah menu
const miningCache = reactive({});
</script>

<script setup>
import { computed, ref, watch } from 'vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useMiningStore } from '@/stores/mining';
import { useToastStore } from '@/stores/toast';
import { downloadCsv } from '@/Utils/exportCsv';

const datasetStore = useDatasetStore();
const miningStore = useMiningStore();
const toast = useToastStore();

const profile = ref(null);
const facts = ref(null);
const recommendations = ref([]);
const algorithms = ref([]);

const isLoadingMetadata = ref(false);
const isRunning = ref(false);

// Fungsi ambil metadata & algoritma dengan sistem Cache
async function fetchMiningMetadata(datasetId, force = false) {
    if (!datasetId) return;

    // 1. Cek Cache: Kalau sudah ada, langsung muat instan tanpa loading
    if (!force && miningCache[datasetId]) {
        const cached = miningCache[datasetId];
        profile.value = cached.profile;
        facts.value = cached.facts;
        recommendations.value = cached.recommendations;
        algorithms.value = cached.algorithms;
        return;
    }

    isLoadingMetadata.value = true;
    try {
        // --- SIMULASI API (Lengkap dengan data pancingan agar UI kartu algoritma muncul) ---
        // Nanti ganti: const response = await axios.get(`/api/datasets/${datasetId}/mining-metadata`);
        const data = await new Promise((resolve) => setTimeout(() => resolve({
            profile: { rowCount: 15200 },
            facts: {
                numericCount: 8, 
                categoricalCount: 4, 
                datetimeCount: 1, 
                outlierRatio: 0.045, 
                duplicateRows: 12, 
                categoricalTargets: [{ name: 'Kategori Produk' }], 
                isTransactional: true
            },
            recommendations: [
                { key: 'association', level: 'high', reason: 'Cocok untuk data transaksional dengan banyak item.' },
                { key: 'clustering', level: 'high', reason: 'Banyak kolom numerik yang ideal untuk dikelompokkan.' }
            ],
            algorithms: [
                { key: 'association', name: 'Association Rules', icon: 'link', description: 'Mencari pola hubungan antar item (market basket analysis).' },
                { key: 'clustering', name: 'Clustering (K-Means)', icon: 'group', description: 'Mengelompokkan baris data ke dalam beberapa klaster kemiripan.' },
                { key: 'classification', name: 'Classification', icon: 'check', description: 'Memprediksi kelas atau kategori target tertentu.' },
                { key: 'regression', name: 'Regression', icon: 'chart', description: 'Memprediksi nilai numerik kontinu berdasarkan fitur.' },
                { key: 'anomaly', name: 'Anomaly Detection', icon: 'warning', description: 'Menemukan baris data yang menyimpang jauh dari kewajaran.' },
                { key: 'timeseries', name: 'Time Series Forecasting', icon: 'clock', description: 'Menganalisis tren data berdasarkan rentang waktu.' }
            ]
        }), 800));
        // ---------------------------------------------------------------------------------

        // 2. Simpan ke Cache
        miningCache[datasetId] = data;

        profile.value = data.profile;
        facts.value = data.facts;
        recommendations.value = data.recommendations;
        algorithms.value = data.algorithms;

    } catch (error) {
        console.error("Gagal mengambil metadata mining:", error);
        toast.push("Gagal memuat rekomendasi algoritma dari server.", "error");
    } finally {
        isLoadingMetadata.value = false;
    }
}

const recommendationFor = (key) =>
    recommendations.value.find((item) => item.key === key) ?? null;

const sortedAlgorithms = computed(() => {
    if (!algorithms.value) return [];
    return [...algorithms.value].sort((a, b) => {
        const rank = (key) => {
            const recommendation = recommendationFor(key);
            if (!recommendation) return 2;
            return recommendation.level === 'high' ? 0 : 1;
        };
        return rank(a.key) - rank(b.key);
    });
});

const session = computed(
    () => miningStore.sessions[Number(datasetStore.selectedId)] ?? null,
);
const selected = computed(() => session.value?.selected ?? []);
const results = computed(() => session.value?.results ?? []);

function setSelection(keys) {
    miningStore.setSelection(datasetStore.selectedId, keys);
}

function toggle(key) {
    setSelection(
        selected.value.includes(key)
            ? selected.value.filter((item) => item !== key)
            : [...selected.value, key],
    );
}

const CHARACTERISTIC_ROWS = computed(() => {
    if (!profile.value || !facts.value) return [];
    return [
        { label: 'Jumlah baris dianalisis', value: profile.value.rowCount?.toLocaleString('id-ID') ?? '-' },
        { label: 'Kolom numerik', value: String(facts.value.numericCount ?? '-') },
        { label: 'Kolom kategorikal', value: String(facts.value.categoricalCount ?? '-') },
        { label: 'Kolom waktu', value: String(facts.value.datetimeCount ?? '-') },
        {
            label: 'Nilai ekstrem',
            value: facts.value.outlierRatio !== undefined 
                ? `${(facts.value.outlierRatio * 100).toFixed(1).replace('.', ',')}% dari sel numerik` 
                : '-'
        },
        { label: 'Baris duplikat', value: facts.value.duplicateRows?.toLocaleString('id-ID') ?? '-' },
        {
            label: 'Kandidat target kategorikal',
            value: facts.value.categoricalTargets?.slice(0, 3).map((c) => c.name).join(', ') || 'tidak ada',
        },
        {
            label: 'Bentuk data',
            value: facts.value.isTransactional ? 'transaksional' : 'tabular biasa',
        },
    ];
});

const CLUSTER_COLUMNS = [
    { key: 'cluster', label: 'Cluster' },
    { key: 'size', label: 'Anggota', align: 'right', numeric: true },
    { key: 'shareLabel', label: 'Porsi', align: 'right', numeric: true },
    { key: 'centerLabel', label: 'Pusat Cluster', wrap: true },
];

const RULE_COLUMNS = [
    { key: 'antecedent', label: 'Jika Membeli', wrap: true },
    { key: 'consequent', label: 'Maka Membeli', wrap: true },
    { key: 'support', label: 'Support', align: 'right', numeric: true },
    { key: 'confidence', label: 'Confidence', align: 'right', numeric: true },
    { key: 'lift', label: 'Lift', align: 'right', numeric: true },
];

const CLASS_COLUMNS = [
    { key: 'label', label: 'Kelas' },
    { key: 'precisionLabel', label: 'Presisi', align: 'right', numeric: true },
    { key: 'recallLabel', label: 'Recall', align: 'right', numeric: true },
    { key: 'f1Label', label: 'F1', align: 'right', numeric: true },
    { key: 'support', label: 'Data Uji', align: 'right', numeric: true },
];

const ANOMALY_COLUMNS = [
    { key: 'cause', label: 'Kolom Pemicu' },
    { key: 'value', label: 'Nilai', align: 'right', numeric: true },
    { key: 'score', label: 'Skor (σ)', align: 'right', numeric: true },
    { key: 'context', label: 'Konteks Baris', wrap: true },
];

async function runAnalysis() {
    if (!selected.value.length) {
        toast.push('Pilih minimal satu algoritma untuk dijalankan.', 'warning');
        return;
    }

    isRunning.value = true;
    try {
        // TODO: Ganti dengan request API ke Backend Python
        // const response = await axios.post(`/api/datasets/${datasetStore.selectedId}/run-mining`, { algorithms: selected.value });
        
        // Simulasi hasil eksekusi
        await new Promise((resolve) => setTimeout(resolve, 1500));
        
        toast.push('Analisis data mining selesai dijalankan oleh server.');
    } catch (error) {
        console.error("Gagal menjalankan algoritma:", error);
        toast.push('Terjadi kesalahan saat mengeksekusi algoritma di server.', 'error');
    } finally {
        isRunning.value = false;
    }
}

function exportRules(payload) {
    downloadCsv(
        'association_rules.csv',
        RULE_COLUMNS.map((column) => column.label),
        payload.rules.map((rule) => [
            rule.antecedent, rule.consequent, rule.support, rule.confidence, rule.lift,
        ]),
    );
    toast.push('Association rule diekspor sebagai CSV.');
}

watch(
    () => datasetStore.selectedId,
    (id) => {
        if (id) {
            fetchMiningMetadata(id);
        } else {
            profile.value = null;
            facts.value = null;
            algorithms.value = [];
        }
    },
    { immediate: true },
);
</script>

<template>
    <PageHeader
        title="Data Mining"
        description="Sistem menganalisis karakteristik dataset lebih dulu, lalu menyarankan algoritma yang sesuai. Pilih satu, beberapa, atau seluruhnya."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Data Mining' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
            <AppButton
                variant="primary"
                icon="play"
                :disabled="isRunning || isLoadingMetadata || !datasetStore.selectedId"
                @click="runAnalysis"
            >
                {{ isRunning ? 'Menjalankan…' : `Jalankan Analisis (${selected.length})` }}
            </AppButton>
        </template>
    </PageHeader>

    <AppCard v-if="!datasetStore.selectedId" flush class="mt-4">
        <EmptyState
            icon="datasets"
            title="Pilih dataset terlebih dahulu"
            description="Silakan pilih dataset dari menu dropdown di atas untuk melihat karakteristik dan rekomendasi algoritma data mining."
        />
    </AppCard>

    <template v-else>
        <AppCard
            class="mt-4"
            title="Karakteristik Dataset"
            subtitle="Dibaca dari hasil profiling; inilah dasar rekomendasi algoritma di bawah."
        >
            <dl v-if="CHARACTERISTIC_ROWS.length" class="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-4">
                <div
                    v-for="row in CHARACTERISTIC_ROWS"
                    :key="row.label"
                    class="min-w-0"
                >
                    <dt class="text-xs text-ink-3">{{ row.label }}</dt>
                    <dd
                        class="mt-0.5 truncate text-sm font-medium text-ink dark:text-ink-dark"
                        :title="row.value"
                    >
                        {{ row.value }}
                    </dd>
                </div>
            </dl>
        </AppCard>

        <div class="mb-3 mt-4 flex flex-wrap items-center gap-3">
            <h2 class="text-sm font-semibold text-ink dark:text-ink-dark">
                Pilih Algoritma
            </h2>
            <span class="text-xs text-ink-3">
                {{ selected.length }} dari {{ sortedAlgorithms.length }} dipilih
            </span>

            <div class="ml-auto flex items-center gap-2">
                <AppButton
                    size="sm"
                    :disabled="isLoadingMetadata"
                    @click="setSelection(sortedAlgorithms.map((item) => item.key))"
                >
                    Pilih Semua
                </AppButton>
                <AppButton size="sm" :disabled="isLoadingMetadata" @click="setSelection([])">
                    Kosongkan
                </AppButton>
            </div>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <button
                v-for="algorithm in sortedAlgorithms"
                :key="algorithm.key"
                type="button"
                class="focus-ring rounded-xl border bg-surface p-5 text-left transition-colors dark:bg-surface-dark"
                :class="
                    selected.includes(algorithm.key)
                        ? 'border-accent ring-1 ring-accent dark:border-accent-dark dark:ring-accent-dark'
                        : 'border-hairline hover:bg-plane dark:border-hairline-dark dark:hover:bg-raised-dark/60'
                "
                :aria-pressed="selected.includes(algorithm.key)"
                @click="toggle(algorithm.key)"
            >
                <div class="flex items-start justify-between gap-3">
                    <span
                        class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-plane text-accent dark:bg-raised-dark dark:text-accent-dark"
                    >
                        <AppIcon :name="algorithm.icon" class="h-[18px] w-[18px]" />
                    </span>

                    <AppIcon
                        v-if="selected.includes(algorithm.key)"
                        name="check"
                        class="h-4 w-4 shrink-0 text-accent dark:text-accent-dark"
                    />
                </div>

                <p class="mt-3.5 flex flex-wrap items-center gap-2">
                    <span class="text-sm font-medium text-ink dark:text-ink-dark">
                        {{ algorithm.name }}
                    </span>
                    <AppBadge
                        v-if="recommendationFor(algorithm.key)?.level === 'high'"
                        variant="good"
                    >
                        Direkomendasikan
                    </AppBadge>
                </p>

                <p class="mt-1 text-sm text-ink-2 dark:text-ink-2-dark">
                    {{ algorithm.description }}
                </p>

                <p class="mt-3 text-xs text-ink-3">
                    {{
                        recommendationFor(algorithm.key)?.reason ??
                        'Tidak menonjol untuk karakteristik dataset ini, tetapi tetap bisa dijalankan.'
                    }}
                </p>
            </button>
        </div>

        <!-- Hasil per algoritma -->
        <div class="mb-3 mt-6 flex flex-wrap items-baseline justify-between gap-2">
            <h2 class="text-sm font-semibold text-ink dark:text-ink-dark">
                Hasil Analisis
            </h2>
            <p v-if="results.length" class="text-xs text-ink-3">
                {{ results.length }} algoritma dijalankan pada dataset terpilih
            </p>
        </div>

        <AppCard v-if="!results.length" flush>
            <EmptyState
                icon="mining"
                title="Belum ada analisis dijalankan"
                description="Pilih algoritma di atas lalu tekan Jalankan Analisis. Setiap algoritma menghasilkan blok hasilnya sendiri."
            />
        </AppCard>

        <div v-else class="space-y-4">
            <!-- Render hasil analisis di sini jika sudah ada data dari backend -->
        </div>
    </template>
</template>