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

// HAPUS IMPORT DATA DAN MESIN ML LOKAL
// import { datasetAnalysis } from '@/Utils/analysis';
// import { analyzeCharacteristics, recommendAlgorithms } from '@/Utils/recommender';
// import { runAnomaly, runAssociation, runClustering, runTimeSeries } from '@/Utils/ml/mining';
// import { trainModel } from '@/Utils/ml/supervised';
// import { mining } from '@/data/placeholder';

const datasetStore = useDatasetStore();
const miningStore = useMiningStore();
const toast = useToastStore();

// 1. STATE UNTUK DATA API
const profile = ref(null);
const facts = ref(null);
const recommendations = ref([]);
const algorithms = ref([]);

const isLoadingMetadata = ref(false);
const isRunning = ref(false);

// 2. MENGAMBIL METADATA DAN DAFTAR ALGORITMA DARI BACKEND
async function fetchMiningMetadata(datasetId) {
    if (!datasetId) return;

    isLoadingMetadata.value = true;
    try {
        // TODO: Ganti dengan pemanggilan API ke Python Backend Anda
        // Contoh: const response = await axios.get(`/api/datasets/${datasetId}/mining-metadata`);
        
        // --- SIMULASI API ---
        const fakeApiResponse = await new Promise(resolve => setTimeout(() => resolve({
            profile: { rowCount: 15200 }, // Data simulasi
            facts: {
                numericCount: 8, categoricalCount: 4, datetimeCount: 1, 
                outlierRatio: 0.045, duplicateRows: 12, 
                categoricalTargets: [{ name: 'Kategori Produk' }], isTransactional: true
            },
            recommendations: [
                { key: 'association', level: 'high', reason: 'Cocok untuk data transaksional.' }
            ],
            algorithms: [
                { key: 'association', name: 'Association Rules', icon: 'link', description: 'Mencari pola pembelian bersama.' },
                { key: 'clustering', name: 'Clustering', icon: 'group', description: 'Mengelompokkan baris berdasarkan kemiripan.' },
                // Tambahkan algoritma lain dari database Anda
            ]
        }), 800));
        // -------------------

        profile.value = fakeApiResponse.profile;
        facts.value = fakeApiResponse.facts;
        recommendations.value = fakeApiResponse.recommendations;
        algorithms.value = fakeApiResponse.algorithms;

    } catch (error) {
        console.error("Gagal mengambil metadata mining:", error);
        toast.push("Gagal memuat rekomendasi algoritma dari server.", "error");
    } finally {
        isLoadingMetadata.value = false;
    }
}

const recommendationFor = (key) =>
    recommendations.value.find((item) => item.key === key) ?? null;

// Mengurutkan algoritma berdasarkan rekomendasi
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

// Gunakan Safe Access (?.) agar UI tidak error jika profile/facts belum tiba dari API
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

// --- Menjalankan algoritma via API --------------------------------------------------

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
        // TODO: Ganti dengan request API (POST) ke Backend Python
        // Contoh: const response = await axios.post(`/api/datasets/${datasetStore.selectedId}/run-mining`, { algorithms: selected.value });

        // --- SIMULASI KOMPUTASI API ---
        const fakeApiResponse = await new Promise((resolve) => setTimeout(() => resolve([
            // Contoh kembalian dari backend untuk association (disesuaikan dengan template)
            {
                key: 'association', name: 'Association Rules', icon: 'link', ok: true,
                payload: {
                    transactions: 1000, columns: ['Item 1', 'Item 2'],
                    rules: [{ antecedent: 'Roti', consequent: 'Susu', support: 0.2, confidence: 0.8, lift: 1.5 }]
                }
            }
        ]), 2000));
        // ------------------------------
        
        miningStore.setResults(datasetStore.selectedId, fakeApiResponse);

        const failed = fakeApiResponse.filter((item) => !item.ok).length;
        toast.push(
            failed
                ? `${fakeApiResponse.length - failed} dari ${fakeApiResponse.length} algoritma selesai, ${failed} dilewati.`
                : `${fakeApiResponse.length} algoritma selesai dijalankan.`,
            failed ? 'warning' : 'success',
        );

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

// 3. TRIGGER PENGAMBILAN DATA KETIKA DATASET BERUBAH
watch(
    () => datasetStore.selectedId,
    (id) => {
        // Kosongkan metadata lama
        profile.value = null;
        facts.value = null;
        algorithms.value = [];
        
        fetchMiningMetadata(id);
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
                :disabled="isRunning || isLoadingMetadata"
                @click="runAnalysis"
            >
                {{ isRunning ? 'Menjalankan…' : `Jalankan Analisis (${selected.length})` }}
            </AppButton>
        </template>
    </PageHeader>

    <AppCard
        title="Karakteristik Dataset"
        subtitle="Dibaca dari hasil profiling; inilah dasar rekomendasi algoritma di bawah."
    >
        <!-- Jika data API belum tiba, render list kosong yang aman tanpa error -->
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
        <!-- Pesan placeholder opsional (jika tidak mau, div ini bisa dihapus) -->
        <p v-else class="text-sm text-ink-3">Menyiapkan karakteristik dataset...</p>
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

    <!-- Kotak Kosong transparan ketika rekomendasi algoritma masih belum tiba -->
    <div v-if="isLoadingMetadata && sortedAlgorithms.length === 0" class="py-8"></div>

    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
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
        <template v-for="result in results" :key="result.key">
            <AppCard v-if="!result.ok" :title="result.name">
                <p class="flex items-start gap-2 text-sm text-ink-2 dark:text-ink-2-dark">
                    <AppIcon
                        name="warning"
                        class="mt-0.5 h-4 w-4 shrink-0 text-[#8a5a00] dark:text-status-warning"
                    />
                    {{ result.message }}
                </p>
            </AppCard>

            <div v-else-if="result.key === 'clustering'" class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <ChartPanel
                    :title="`${result.name} — sebaran cluster`"
                    :subtitle="`K-Means, k = ${result.payload.k}, konvergen dalam ${result.payload.iterations} iterasi`"
                    type="scatter"
                    :series="result.payload.series"
                    :height="300"
                />
                <AppCard
                    title="Ringkasan Cluster"
                    :subtitle="`Dihitung dari kolom: ${result.payload.columns.join(', ')}`"
                    flush
                >
                    <DataTable :columns="CLUSTER_COLUMNS" :rows="result.payload.clusters" />
                </AppCard>
            </div>

            <AppCard
                v-else-if="result.key === 'classification'"
                :title="`${result.name} — target ${result.payload.target}`"
                :subtitle="`${result.payload.algorithm} · ${result.payload.trainSize} baris latih, ${result.payload.testSize} baris uji`"
                flush
            >
                <template #actions>
                    <AppBadge variant="good">
                        Akurasi {{ result.payload.accuracy }}
                    </AppBadge>
                </template>

                <DataTable :columns="CLASS_COLUMNS" :rows="result.payload.perClass" />
            </AppCard>

            <div v-else-if="result.key === 'regression'" class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <ChartPanel
                    :title="`${result.name} — prediksi vs aktual`"
                    :subtitle="`Target ${result.payload.target} · titik ideal berada di garis diagonal`"
                    type="scatter"
                    :series="[{ label: 'Baris data uji', data: result.payload.scatter }]"
                    :height="300"
                />
                <AppCard
                    title="Kualitas Model"
                    :subtitle="result.payload.algorithm"
                >
                    <dl class="space-y-3.5">
                        <div
                            v-for="row in [
                                { label: 'R² (data uji)', value: result.payload.r2 },
                                { label: 'RMSE', value: result.payload.rmse },
                                { label: 'Baris uji', value: String(result.payload.testSize) },
                            ]"
                            :key="row.label"
                            class="flex items-center justify-between gap-4 border-b border-hairline pb-3.5 last:border-0 last:pb-0 dark:border-hairline-dark"
                        >
                            <dt class="text-sm text-ink-2 dark:text-ink-2-dark">
                                {{ row.label }}
                            </dt>
                            <dd class="text-sm font-medium tabular-nums text-ink dark:text-ink-dark">
                                {{ row.value }}
                            </dd>
                        </div>
                    </dl>
                </AppCard>
            </div>

            <AppCard
                v-else-if="result.key === 'association'"
                :title="`${result.name} — aturan dengan lift tertinggi`"
                :subtitle="`${result.payload.transactions} transaksi · kolom item: ${result.payload.columns.join(', ')}`"
                flush
            >
                <template #actions>
                    <AppButton
                        size="sm"
                        icon="download"
                        @click="exportRules(result.payload)"
                    >
                        Ekspor
                    </AppButton>
                </template>

                <DataTable
                    v-if="result.payload.rules.length"
                    :columns="RULE_COLUMNS"
                    :rows="result.payload.rules"
                >
                    <template #cell-antecedent="{ row }">
                        <span class="font-medium text-ink dark:text-ink-dark">
                            {{ row.antecedent }}
                        </span>
                    </template>

                    <template #cell-consequent="{ row }">
                        <span class="flex items-center gap-1.5">
                            <AppIcon
                                name="chevronRight"
                                class="h-3 w-3 shrink-0 text-ink-3"
                            />
                            <span class="font-medium text-ink dark:text-ink-dark">
                                {{ row.consequent }}
                            </span>
                        </span>
                    </template>
                </DataTable>

                <EmptyState
                    v-else
                    icon="datasets"
                    title="Tidak ada aturan yang lolos ambang"
                    description="Tidak ditemukan pasangan item dengan support, confidence, dan lift di atas ambang minimum."
                />
            </AppCard>

            <div v-else-if="result.key === 'anomaly'" class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <ChartPanel
                    :title="`${result.name} — ${result.payload.count} baris menyimpang`"
                    :subtitle="`Sumbu: ${result.payload.axes[0]} dan ${result.payload.axes[1]}`"
                    type="scatter"
                    :series="result.payload.series"
                    :height="300"
                />
                <AppCard
                    title="Anomali Teratas"
                    :subtitle="`${(result.payload.ratio * 100).toFixed(1).replace('.', ',')}% dari ${result.payload.checked} baris diperiksa`"
                    flush
                >
                    <DataTable
                        v-if="result.payload.top.length"
                        :columns="ANOMALY_COLUMNS"
                        :rows="result.payload.top"
                    />
                    <EmptyState
                        v-else
                        icon="check"
                        title="Tidak ada anomali"
                        description="Seluruh baris berada dalam batas wajar pada ambang yang dipakai."
                    />
                </AppCard>
            </div>

            <ChartPanel
                v-else-if="result.key === 'timeseries'"
                :title="`${result.name} — ${result.payload.valueColumn}`"
                :subtitle="`Agregasi ${result.payload.grain === 'month' ? 'bulanan' : 'harian'} atas ${result.payload.timeColumn} · tren ${result.payload.direction}, proyeksi ${result.payload.horizon} periode`"
                type="line"
                :labels="result.payload.labels"
                :series="result.payload.series"
                :height="320"
            />
        </template>
    </div>
</template>