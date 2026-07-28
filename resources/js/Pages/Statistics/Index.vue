<script setup>
import { computed, ref, watch } from 'vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useAnalysis } from '@/Composables/useAnalysis';
import { formatNumber } from '@/Utils/profiler';

/*
 * Analisis Statistik dua bagian:
 *   1. Deskriptif — mean/median/modus/varians/kuartil/persentil/skewness/
 *      kurtosis seluruh kolom numerik (python/stats/descriptive.py).
 *   2. Inferensial — tujuh uji hipotesis dengan kesimpulan kalimat biasa
 *      (python/stats/inferential.py).
 */
const descriptive = useAnalysis('descriptive');
const inferential = useAnalysis('inferential', { autoLoad: false });

const datasetStore = descriptive.datasetStore;

const numericColumns = computed(() =>
    datasetStore.columns.filter(
        (column) => ['integer', 'float'].includes(column.type) && !column.is_identifier,
    ),
);

const groupColumns = computed(() =>
    datasetStore.columns.filter(
        (column) => column.type === 'category' && !column.is_identifier && column.unique <= 20,
    ),
);

const TESTS = [
    { value: 't_test', label: 'T-Test (2 kelompok)', needs: 'group' },
    { value: 'anova', label: 'ANOVA (3+ kelompok)', needs: 'group' },
    { value: 'mann_whitney', label: 'Mann-Whitney (non-parametrik, 2 kelompok)', needs: 'group' },
    { value: 'kruskal', label: 'Kruskal-Wallis (non-parametrik, 3+ kelompok)', needs: 'group' },
    { value: 'chi_square', label: 'Chi-Square (kategori × kategori)', needs: 'xy_cat' },
    { value: 'pearson', label: 'Korelasi Pearson (numerik × numerik)', needs: 'xy_num' },
    { value: 'spearman', label: 'Korelasi Spearman (numerik × numerik)', needs: 'xy_num' },
];

const form = ref({ test: 't_test', value: '', group: '', x: '', y: '' });
const needs = computed(() => TESTS.find((test) => test.value === form.value.test)?.needs);

// Isi pilihan awal begitu kolom dataset termuat, supaya dropdown tidak kosong
// dan pengguna bisa langsung menekan Jalankan Uji.
watch([() => datasetStore.columns, needs], () => {
    const numericPool = numericColumns.value;
    const groupPool = groupColumns.value;
    const xyPool = needs.value === 'xy_cat' ? groupPool : numericPool;

    if (!form.value.value || !numericPool.some((c) => c.name === form.value.value)) {
        form.value.value = numericPool[0]?.name ?? '';
    }

    if (!form.value.group || !groupPool.some((c) => c.name === form.value.group)) {
        form.value.group = groupPool[0]?.name ?? '';
    }

    if (!xyPool.some((c) => c.name === form.value.x)) {
        form.value.x = xyPool[0]?.name ?? '';
    }

    if (!xyPool.some((c) => c.name === form.value.y)) {
        form.value.y = xyPool[1]?.name ?? xyPool[0]?.name ?? '';
    }
}, { immediate: true });

function runTest() {
    const payload = { test: form.value.test };

    if (needs.value === 'group') {
        payload.value = form.value.value || numericColumns.value[0]?.name;
        payload.group = form.value.group || groupColumns.value[0]?.name;
    } else {
        const pool = needs.value === 'xy_cat' ? groupColumns.value : numericColumns.value;

        payload.x = form.value.x || pool[0]?.name;
        payload.y = form.value.y || (pool[1]?.name ?? pool[0]?.name);
    }

    inferential.run(payload);
}

const DESCRIPTIVE_COLUMNS = [
    { key: 'column', label: 'Kolom' },
    { key: 'mean', label: 'Mean', align: 'right', numeric: true },
    { key: 'median', label: 'Median', align: 'right', numeric: true },
    { key: 'mode', label: 'Modus', align: 'right', numeric: true },
    { key: 'std', label: 'Std Dev', align: 'right', numeric: true },
    { key: 'variance', label: 'Varians', align: 'right', numeric: true },
    { key: 'q1', label: 'Q1', align: 'right', numeric: true },
    { key: 'q3', label: 'Q3', align: 'right', numeric: true },
    { key: 'skewness', label: 'Skewness', align: 'right', numeric: true },
    { key: 'kurtosis', label: 'Kurtosis', align: 'right', numeric: true },
];

const fmt = (value, digits = 2) =>
    value === null || value === undefined
        ? '—'
        : Number(value) === Math.round(Number(value)) && Math.abs(value) < 10_000
          ? Number(value).toLocaleString('id-ID')
          : formatNumber(Number(value));

const FIELD =
    'focus-ring h-9 w-full rounded-lg border-hairline bg-plane py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark';
</script>

<template>
    <PageHeader
        title="Analisis Statistik"
        description="Statistik deskriptif seluruh kolom numerik, dan uji inferensial untuk menguji dugaan antar kolom."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Analisis Statistik' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
            <AppButton
                variant="primary"
                icon="play"
                :disabled="descriptive.isRunning.value"
                @click="descriptive.run()"
            >
                {{ descriptive.isRunning.value ? 'Menghitung…' : 'Hitung Deskriptif' }}
            </AppButton>
        </template>
    </PageHeader>

    <!-- Deskriptif -->
    <AppCard v-if="!descriptive.result.value && !descriptive.isLoading.value" flush>
        <EmptyState
            icon="statistical-analysis"
            title="Belum ada statistik deskriptif"
            description="Hitung mean, median, modus, varians, simpangan baku, kuartil, persentil, skewness, dan kurtosis seluruh kolom numerik."
        >
            <template #action>
                <AppButton variant="primary" icon="play" @click="descriptive.run()">
                    Hitung Deskriptif
                </AppButton>
            </template>
        </EmptyState>
    </AppCard>

    <template v-else-if="descriptive.result.value">
        <AppCard
            title="Statistik Deskriptif"
            :subtitle="`${descriptive.result.value.columns.length} kolom numerik dari ${descriptive.result.value.row_count.toLocaleString('id-ID')} baris`"
            flush
        >
            <DataTable
                :columns="DESCRIPTIVE_COLUMNS"
                :rows="descriptive.result.value.columns"
                row-key="column"
            >
                <template #cell-column="{ row }">
                    <span class="font-medium text-ink dark:text-ink-dark">{{ row.column }}</span>
                </template>
                <template v-for="key in ['mean', 'median', 'mode', 'std', 'variance', 'q1', 'q3']" #[`cell-${key}`]="{ row }" :key="key">
                    {{ fmt(row[key]) }}
                </template>
                <template #cell-skewness="{ row }">{{ row.skewness?.toFixed(2)?.replace('.', ',') ?? '—' }}</template>
                <template #cell-kurtosis="{ row }">{{ row.kurtosis?.toFixed(2)?.replace('.', ',') ?? '—' }}</template>
            </DataTable>
        </AppCard>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <AppCard title="Interpretasi per Kolom" subtitle="Ringkasan bentuk sebaran dalam kalimat.">
                <ul class="space-y-3">
                    <li
                        v-for="column in descriptive.result.value.columns"
                        :key="column.column"
                        class="text-sm text-ink-2 dark:text-ink-2-dark"
                    >
                        <span class="font-medium text-ink dark:text-ink-dark">{{ column.column }}:</span>
                        {{ column.interpretation }}
                    </li>
                </ul>
            </AppCard>

            <AppCard
                v-if="descriptive.result.value.categorical?.length"
                title="Kolom Kategorikal"
                subtitle="Modus dan konsentrasinya."
            >
                <ul class="space-y-3">
                    <li
                        v-for="column in descriptive.result.value.categorical"
                        :key="column.column"
                        class="text-sm text-ink-2 dark:text-ink-2-dark"
                    >
                        <span class="font-medium text-ink dark:text-ink-dark">{{ column.column }}:</span>
                        {{ column.interpretation }}
                    </li>
                </ul>
            </AppCard>
        </div>
    </template>

    <!-- Inferensial -->
    <div class="mb-3 mt-6 flex flex-wrap items-baseline justify-between gap-2">
        <h2 class="text-sm font-semibold text-ink dark:text-ink-dark">Statistik Inferensial</h2>
        <p class="text-xs text-ink-3">T-Test, ANOVA, Chi-Square, Pearson, Spearman, Mann-Whitney, Kruskal-Wallis</p>
    </div>

    <AppCard title="Uji Hipotesis" subtitle="Pilih uji dan kolomnya; kesimpulan ditulis dalam kalimat biasa pada taraf 5%.">
        <div class="grid grid-cols-1 items-end gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
                <label for="stat-test" class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Jenis Uji</label>
                <select id="stat-test" v-model="form.test" :class="FIELD">
                    <option v-for="test in TESTS" :key="test.value" :value="test.value">{{ test.label }}</option>
                </select>
            </div>

            <template v-if="needs === 'group'">
                <div>
                    <label for="stat-value" class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Kolom Nilai (numerik)</label>
                    <select id="stat-value" v-model="form.value" :class="FIELD">
                        <option v-for="column in numericColumns" :key="column.name" :value="column.name">{{ column.name }}</option>
                    </select>
                </div>
                <div>
                    <label for="stat-group" class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Kolom Kelompok</label>
                    <select id="stat-group" v-model="form.group" :class="FIELD">
                        <option v-for="column in groupColumns" :key="column.name" :value="column.name">{{ column.name }} ({{ column.unique }} kelompok)</option>
                    </select>
                </div>
            </template>

            <template v-else>
                <div>
                    <label for="stat-x" class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Kolom X</label>
                    <select id="stat-x" v-model="form.x" :class="FIELD">
                        <option
                            v-for="column in needs === 'xy_cat' ? groupColumns : numericColumns"
                            :key="column.name" :value="column.name"
                        >{{ column.name }}</option>
                    </select>
                </div>
                <div>
                    <label for="stat-y" class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Kolom Y</label>
                    <select id="stat-y" v-model="form.y" :class="FIELD">
                        <option
                            v-for="column in needs === 'xy_cat' ? groupColumns : numericColumns"
                            :key="column.name" :value="column.name"
                        >{{ column.name }}</option>
                    </select>
                </div>
            </template>

            <AppButton variant="primary" icon="play" :disabled="inferential.isRunning.value" @click="runTest">
                {{ inferential.isRunning.value ? 'Menguji…' : 'Jalankan Uji' }}
            </AppButton>
        </div>

        <template v-if="inferential.result.value" #footer>
            <div class="space-y-4">
                <div class="flex flex-wrap items-center gap-2">
                    <AppBadge :variant="inferential.result.value.significant ? 'good' : 'neutral'">
                        {{ inferential.result.value.significant ? 'Signifikan' : 'Tidak signifikan' }}
                    </AppBadge>
                    <AppBadge>p = {{ inferential.result.value.p_value?.toExponential(3) }}</AppBadge>
                    <AppBadge v-if="inferential.result.value.statistic !== undefined">
                        statistik = {{ Number(inferential.result.value.statistic ?? inferential.result.value.coefficient).toFixed(4).replace('.', ',') }}
                    </AppBadge>
                    <AppBadge v-if="inferential.result.value.effect_size">
                        {{ inferential.result.value.effect_size.name }} =
                        {{ inferential.result.value.effect_size.value.toFixed(3).replace('.', ',') }}
                        ({{ inferential.result.value.effect_size.magnitude }})
                    </AppBadge>
                </div>

                <p class="flex items-start gap-2 text-sm text-ink dark:text-ink-dark">
                    <AppIcon
                        :name="inferential.result.value.significant ? 'check' : 'warning'"
                        class="mt-0.5 h-4 w-4 shrink-0"
                        :class="inferential.result.value.significant
                            ? 'text-[#006300] dark:text-status-good'
                            : 'text-ink-3'"
                    />
                    {{ inferential.result.value.conclusion }}
                </p>

                <p v-if="inferential.result.value.note" class="text-xs text-ink-3">
                    {{ inferential.result.value.note }}
                </p>

                <div v-if="inferential.result.value.groups?.length" class="overflow-hidden rounded-lg border border-hairline dark:border-hairline-dark">
                    <DataTable
                        :columns="[
                            { key: 'label', label: 'Kelompok' },
                            { key: 'n', label: 'N', align: 'right', numeric: true },
                            { key: 'mean', label: 'Mean', align: 'right', numeric: true },
                            { key: 'median', label: 'Median', align: 'right', numeric: true },
                            { key: 'std', label: 'Std Dev', align: 'right', numeric: true },
                        ]"
                        :rows="inferential.result.value.groups"
                        row-key="label"
                    >
                        <template v-for="key in ['mean', 'median', 'std']" #[`cell-${key}`]="{ row }" :key="key">
                            {{ fmt(row[key]) }}
                        </template>
                    </DataTable>
                </div>
            </div>
        </template>
    </AppCard>
</template>
