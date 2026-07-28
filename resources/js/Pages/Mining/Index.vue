<script setup>
import { computed, ref } from 'vue';
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
import { datasetAnalysis } from '@/Utils/analysis';
import { analyzeCharacteristics, recommendAlgorithms } from '@/Utils/recommender';
import {
    runAnomaly,
    runAssociation,
    runClustering,
    runTimeSeries,
} from '@/Utils/ml/mining';
import { trainModel } from '@/Utils/ml/supervised';
import { asDecimal, asPercent } from '@/Utils/ml/metrics';
import { isNumericType } from '@/Utils/profiler';
import { downloadCsv } from '@/Utils/exportCsv';
import { mining } from '@/data/placeholder';

/*
 * Alurnya: baca karakteristik dataset -> tawarkan algoritma yang sesuai ->
 * pengguna memilih satu, beberapa, atau semuanya -> seluruh pilihan dijalankan
 * dan masing-masing menghasilkan blok hasil sendiri.
 *
 * Rekomendasi hanya menandai dan mengurutkan; tidak ada algoritma yang dikunci,
 * karena dugaan sistem soal "kolom target" bisa saja tidak sesuai maksud
 * pengguna. Alasan rekomendasi selalu menyebut kolom yang mendasarinya
 * (lihat `@/Utils/recommender`).
 */
const datasetStore = useDatasetStore();
const miningStore = useMiningStore();
const toast = useToastStore();

const analysis = computed(() => datasetAnalysis(datasetStore.selectedId));
const profile = computed(() => analysis.value.profile);
const facts = computed(() =>
    analyzeCharacteristics(profile.value, analysis.value.table),
);
const recommendations = computed(() =>
    recommendAlgorithms(profile.value, analysis.value.table),
);

const recommendationFor = (key) =>
    recommendations.value.find((item) => item.key === key) ?? null;

// Algoritma yang direkomendasikan naik ke atas; sisanya menyusul dengan urutan
// aslinya sehingga posisi kartu tetap dapat diprediksi.
const algorithms = computed(() =>
    [...mining.algorithms].sort((a, b) => {
        const rank = (key) => {
            const recommendation = recommendationFor(key);

            if (!recommendation) {
                return 2;
            }

            return recommendation.level === 'high' ? 0 : 1;
        };

        return rank(a.key) - rank(b.key);
    }),
);

const isRunning = ref(false);

/*
 * Pilihan algoritma dan hasilnya disimpan di store per dataset, bukan di dalam
 * komponen: analisis yang sudah dijalankan harus tetap bisa dilihat lagi setelah
 * pengguna berpindah menu dan kembali.
 */
const session = computed(
    () => miningStore.sessions[Number(datasetStore.selectedId)] ?? null,
);

// Pilihan dibiarkan kosong sampai pengguna memilih sendiri. Rekomendasi hanya
// menandai dan mengurutkan kartu — mencentangkannya otomatis akan membuat
// analisis berjalan atas dugaan sistem, bukan atas keputusan pengguna.
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

const CHARACTERISTIC_ROWS = computed(() => [
    { label: 'Jumlah baris dianalisis', value: profile.value.rowCount.toLocaleString('id-ID') },
    { label: 'Kolom numerik', value: String(facts.value.numericCount) },
    { label: 'Kolom kategorikal', value: String(facts.value.categoricalCount) },
    { label: 'Kolom waktu', value: String(facts.value.datetimeCount) },
    {
        label: 'Nilai ekstrem',
        value: `${(facts.value.outlierRatio * 100).toFixed(1).replace('.', ',')}% dari sel numerik`,
    },
    { label: 'Baris duplikat', value: facts.value.duplicateRows.toLocaleString('id-ID') },
    {
        label: 'Kandidat target kategorikal',
        value:
            facts.value.categoricalTargets
                .slice(0, 3)
                .map((column) => column.name)
                .join(', ') || 'tidak ada',
    },
    {
        label: 'Bentuk data',
        value: facts.value.isTransactional ? 'transaksional' : 'tabular biasa',
    },
]);

// --- Menjalankan algoritma --------------------------------------------------

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

/** Fitur untuk model: seluruh kolom yang bisa dianalisis selain targetnya. */
function featuresFor(target) {
    return profile.value.columns
        .filter(
            (column) =>
                !column.isIdentifier &&
                column.name !== target &&
                column.type !== 'datetime' &&
                (isNumericType(column.type) || column.unique <= 12),
        )
        .map((column) => column.name);
}

function runClassification() {
    const target = facts.value.categoricalTargets[0];

    if (!target) {
        return { ok: false, message: 'Tidak ada kolom kategorikal yang layak jadi target.' };
    }

    const result = trainModel({
        table: analysis.value.table,
        profile: profile.value,
        target: target.name,
        features: featuresFor(target.name),
    });

    if (!result.ok) {
        return result;
    }

    const { evaluation, ...model } = result.model;

    return {
        ok: true,
        payload: {
            target: target.name,
            algorithm: model.algorithm,
            trainSize: model.trainSize,
            testSize: model.testSize,
            accuracy: asPercent(evaluation.accuracy),
            f1: asPercent(evaluation.f1),
            perClass: evaluation.perClass.map((item, index) => ({
                id: index,
                label: item.label,
                precisionLabel: asPercent(item.precision),
                recallLabel: asPercent(item.recall),
                f1Label: asPercent(item.f1),
                support: item.support,
            })),
        },
    };
}

function runRegression() {
    const candidate = facts.value.numericTargets[0];

    if (!candidate) {
        return { ok: false, message: 'Tidak ada kolom numerik yang layak jadi target.' };
    }

    const target = candidate.column.name;
    const result = trainModel({
        table: analysis.value.table,
        profile: profile.value,
        target,
        features: featuresFor(target).filter((feature) => {
            const column = profile.value.columns.find((item) => item.name === feature);

            return isNumericType(column.type);
        }),
    });

    if (!result.ok) {
        return result;
    }

    const model = result.model;

    return {
        ok: true,
        payload: {
            target,
            algorithm: model.algorithm,
            r2: asDecimal(model.evaluation.r2),
            rmse: model.evaluation.rmse.toLocaleString('id-ID', {
                maximumFractionDigits: 0,
            }),
            testSize: model.testSize,
            scatter: model.scatter,
            coefficients: model.coefficients,
        },
    };
}

const RUNNERS = {
    clustering: () => {
        const result = runClustering({
            table: analysis.value.table,
            profile: profile.value,
            k: 3,
        });

        return result.ok
            ? {
                  ok: true,
                  payload: {
                      ...result,
                      clusters: result.clusters.map((cluster) => ({
                          ...cluster,
                          id: cluster.cluster,
                          shareLabel: `${cluster.share.toFixed(1).replace('.', ',')}%`,
                          centerLabel: result.columns
                              .map(
                                  (column, index) =>
                                      `${column}: ${cluster.center[index].toLocaleString('id-ID')}`,
                              )
                              .join(' · '),
                      })),
                  },
              }
            : result;
    },
    classification: runClassification,
    regression: runRegression,
    association: () => {
        const result = runAssociation({
            table: analysis.value.table,
            profile: profile.value,
        });

        return result.ok ? { ok: true, payload: result } : result;
    },
    anomaly: () => {
        const result = runAnomaly({
            table: analysis.value.table,
            profile: profile.value,
        });

        return result.ok ? { ok: true, payload: result } : result;
    },
    timeseries: () => {
        const result = runTimeSeries({
            table: analysis.value.table,
            profile: profile.value,
        });

        return result.ok ? { ok: true, payload: result } : result;
    },
};

function runAnalysis() {
    if (!selected.value.length) {
        toast.push('Pilih minimal satu algoritma untuk dijalankan.', 'warning');

        return;
    }

    isRunning.value = true;

    // Perhitungan berjalan di thread yang sama; jeda satu frame memberi
    // kesempatan tombol berganti label sebelum browser sibuk menghitung.
    setTimeout(() => {
        const completed = [];

        for (const key of selected.value) {
            const meta = mining.algorithms.find((item) => item.key === key);
            const outcome = RUNNERS[key]();

            completed.push({
                key,
                name: meta?.name ?? key,
                icon: meta?.icon ?? 'mining',
                ok: outcome.ok,
                message: outcome.message ?? null,
                payload: outcome.payload ?? null,
            });
        }

        miningStore.setResults(datasetStore.selectedId, completed);
        isRunning.value = false;

        const failed = completed.filter((item) => !item.ok).length;

        toast.push(
            failed
                ? `${completed.length - failed} dari ${completed.length} algoritma selesai, ${failed} dilewati.`
                : `${completed.length} algoritma selesai dijalankan.`,
            failed ? 'warning' : 'success',
        );
    }, 16);
}

function exportRules(payload) {
    downloadCsv(
        'association_rules.csv',
        RULE_COLUMNS.map((column) => column.label),
        payload.rules.map((rule) => [
            rule.antecedent,
            rule.consequent,
            rule.support,
            rule.confidence,
            rule.lift,
        ]),
    );
    toast.push('Association rule diekspor sebagai CSV.');
}
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
                :disabled="isRunning"
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
        <dl class="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-4">
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
            {{ selected.length }} dari {{ algorithms.length }} dipilih
        </span>

        <div class="ml-auto flex items-center gap-2">
            <AppButton
                size="sm"
                @click="setSelection(algorithms.map((item) => item.key))"
            >
                Pilih Semua
            </AppButton>
            <AppButton size="sm" @click="setSelection([])">Kosongkan</AppButton>
        </div>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <button
            v-for="algorithm in algorithms"
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
            <!-- Algoritma yang tidak cocok tetap dilaporkan, bukan dihilangkan
                 diam-diam, supaya pengguna tahu mengapa hasilnya tidak ada. -->
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
