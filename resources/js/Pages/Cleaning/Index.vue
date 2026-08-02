<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useToastStore } from '@/stores/toast';
import { api } from '@/Utils/api';
import { downloadCsv } from '@/Utils/exportCsv';

const datasetStore = useDatasetStore();
const toast = useToastStore();

const issues = ref([]);
const strategies = ref([]);
const impact = ref({ labels: [], series: [] });
const preview = ref({ before: null, after: null });
const cleaningResult = ref(null);

const isLoading = ref(false);
const isApplying = ref(false);
const downloadDialogOpen = ref(false);
const downloadDialogMessage = ref('');
const activeTab = ref('missing');

const missingColumnMethods = ref({});
const missingCustomValues = ref({});
const duplicateSubset = ref([]);
const duplicateKeep = ref('keep_first');
const outlierMethod = ref('iqr');
const outlierThreshold = ref(1.5);
const outlierAction = ref('drop');
const outlierColumns = ref([]);
const textCleaningOptions = ref({
    trim: true,
    lower: false,
    upper: false,
    title: false,
    remove_special: false,
    remove_digits: false,
    remove_html_url: false,
});
const textColumnsSelected = ref([]);
const typeCastingSelections = ref({});

const selectedDatasetId = computed(() => datasetStore.selectedId);
const actionsLocked = computed(() => isLoading.value || isApplying.value || datasetStore.isLoading);

const ISSUE_TONES = {
    warning: 'text-[#8a5a00] dark:text-status-warning',
    serious: 'text-[#a34418] dark:text-status-serious',
    critical: 'text-status-critical',
};

const allColumns = computed(() => datasetStore.columns ?? []);
const comparableColumns = computed(() =>
    allColumns.value
        .filter((column) => !['id', 'identifier'].includes(column.type))
        .map((column) => column.name),
);
const numericColumns = computed(() =>
    allColumns.value
        .filter((column) => ['integer', 'float', 'numeric', 'number'].includes(column.type))
        .map((column) => column.name),
);
const textColumns = computed(() =>
    allColumns.value
        .filter((column) => ['text', 'category', 'string'].includes(column.type))
        .map((column) => column.name),
);
const missingColumnDetails = computed(() => issues.value.find((issue) => issue.key === 'missing')?.details ?? []);
const duplicateColumnDetails = computed(() => issues.value.find((issue) => issue.key === 'duplicate')?.details?.map(d => d.column) ?? []);
const outlierColumnDetails = computed(() => issues.value.find((issue) => issue.key === 'outlier')?.details?.map(d => d.column) ?? []);
const textColumnDetails = computed(() => issues.value.find((issue) => issue.key === 'type')?.details?.map(d => d.column) ?? []);

const previewColumns = (view) => view?.columns ?? [];
const previewRows = (view) => view?.rows ?? [];

const tabOptions = [
    { key: 'missing', label: 'Missing Values' },
    { key: 'duplicate', label: 'Duplicates' },
    { key: 'outlier', label: 'Outliers' },
    { key: 'text', label: 'Text Cleaning' },
    { key: 'type', label: 'Type Casting & Normalization' },
];

const missingMethodOptions = [
    { value: 'drop_rows', label: 'Drop Rows' },
    { value: 'mean', label: 'Mean' },
    { value: 'median', label: 'Median' },
    { value: 'mode', label: 'Mode' },
    { value: 'custom_value', label: 'Custom Value' },
];
const duplicateKeepOptions = [
    { value: 'keep_first', label: 'Keep First' },
    { value: 'keep_last', label: 'Keep Last' },
    { value: 'drop_all', label: 'Drop All' },
];
const outlierMethodOptions = [
    { value: 'iqr', label: 'IQR' },
    { value: 'zscore', label: 'Z-Score' },
];
const outlierActionOptions = [
    { value: 'drop', label: 'Drop' },
    { value: 'winsorize', label: 'Cap / Winsorize' },
];
const textCleaningOptionsList = [
    { key: 'trim', label: 'Trim Whitespace' },
    { key: 'lower', label: 'Lowercase' },
    { key: 'upper', label: 'Uppercase' },
    { key: 'title', label: 'Titlecase' },
    { key: 'remove_special', label: 'Hapus Karakter Spesial/Simbol' },
    { key: 'remove_digits', label: 'Hapus Angka' },
    { key: 'remove_html_url', label: 'Hapus Tag HTML/URL' },
];
const typeCastingOptions = [
    { value: 'string', label: 'String' },
    { value: 'integer', label: 'Integer' },
    { value: 'float', label: 'Float' },
    { value: 'datetime', label: 'DateTime' },
    { value: 'boolean', label: 'Boolean' },
];

function setDefaultState() {
    issues.value = [];
    strategies.value = [];
    impact.value = { labels: [], series: [] };
    preview.value = { before: null, after: null };
    cleaningResult.value = null;
    activeTab.value = 'missing';
    missingColumnMethods.value = {};
    missingCustomValues.value = {};
    duplicateSubset.value = [];
    duplicateKeep.value = 'keep_first';
    outlierMethod.value = 'iqr';
    outlierThreshold.value = 1.5;
    outlierAction.value = 'drop';
    outlierColumns.value = numericColumns.value.slice();
    textCleaningOptions.value = {
        trim: true,
        lower: false,
        upper: false,
        title: false,
        remove_special: false,
        remove_digits: false,
        remove_html_url: false,
    };
    textColumnsSelected.value = textColumns.value.slice();
    typeCastingSelections.value = Object.fromEntries(
        allColumns.value.map((column) => [column.name, column.type ?? 'string']),
    );
}

function buildAuditRows(result) {
    const rowsBefore = result?.impact?.rows?.[0] ?? datasetStore.selectedDetail?.rows ?? '—';
    const rowsAfter = result?.impact?.rows?.[1] ?? '—';

    return [
        ['Dataset', datasetStore.selected?.name ?? datasetStore.selectedId ?? '—'],
        ['Baris Awal', rowsBefore],
        ['Baris Sesudah', rowsAfter],
        ['Baris Dihapus', result?.rows_removed ?? 0],
        ['Missing Sebelum', result?.missing?.before ?? 0],
        ['Missing Sesudah', result?.missing?.after ?? 0],
        ['Duplikat Dihapus', result?.duplicates?.removed ?? 0],
        ['Outlier Ditangani', result?.outliers?.affected ?? 0],
        ['Normalisasi Teks', result?.text?.affected ?? 0],
        ['Strategi Duplikat', duplicateKeep.value || '—'],
        ['Strategi Outlier', buildOutlierStrategy().method || '—'],
        ['Strategi Teks', buildTextStrategy().method || '—'],
        ['Type Casting', Object.values(typeCastingSelections.value).join(', ') || '—'],
    ];
}

function initMissingMethods() {
    missingColumnMethods.value = Object.fromEntries(
        missingColumnDetails.value.map((detail) => [
            detail.column,
            detail.recommended_strategy || 'median',
        ]),
    );
}

function initTypeCasting() {
    typeCastingSelections.value = Object.fromEntries(
        allColumns.value.map((column) => [column.name, column.type ?? 'string']),
    );
}

function prepareMissingValues(details) {
    missingCustomValues.value = Object.fromEntries(
        (details ?? []).map((detail) => [
            detail.column,
            detail.recommended_custom_value ?? 'Unknown',
        ]),
    );
}

function previewCellChanged(rowIndex, columnIndex) {
    const before = previewRows(preview.before)[rowIndex]?.[columnIndex];
    const after = previewRows(preview.after)[rowIndex]?.[columnIndex];
    return before !== after;
}

function normalizeImpact(data) {
    if (Array.isArray(data?.series) && data.series.length) {
        return data;
    }

    if (!Array.isArray(data?.rows)) {
        return data ?? { labels: [], series: [] };
    }

    return {
        ...data,
        labels: data.labels ?? ['Sebelum', 'Sesudah'],
        series: [
            { label: 'Baris Valid', data: [data.rows[0] ?? 0, data.rows[1] ?? 0] },
            { label: 'Baris Bermasalah', data: [data.missing_cells?.[0] ?? 0, data.missing_cells?.[1] ?? 0] },
        ],
    };
}

function buildMissingStrategy() {
    const columns = missingColumnDetails.value.map((detail) => detail.column);
    const methods = columns.map((name) => missingColumnMethods.value[name] || 'median');
    const uniqueMethods = [...new Set(methods)];
    const method = uniqueMethods.length === 1
        ? uniqueMethods[0]
        : uniqueMethods.includes('custom_value')
            ? 'custom_value'
            : uniqueMethods[0] ?? 'median';

    const strategy = { method, columns };
    if (method === 'custom_value') {
        strategy.custom_values = Object.fromEntries(
            columns
                .map((name) => [name, missingCustomValues.value[name] ?? 'Unknown'])
                .filter(([, value]) => String(value ?? '').trim().length > 0),
        );
    }

    return strategy;
}

function buildDuplicateStrategy() {
    return {
        subset: duplicateSubset.value.length ? duplicateSubset.value : comparableColumns.value,
        keep: duplicateKeep.value,
    };
}

function buildOutlierStrategy() {
    // prefer problematic numeric columns when available; otherwise fall back to selected/outlierColumns or all numeric columns
    const columns = outlierColumns.value.length ? outlierColumns.value : (outlierColumnDetails.value.length ? outlierColumnDetails.value : numericColumns.value);
    const method = outlierAction.value === 'winsorize'
        ? 'winsorize'
        : outlierMethod.value === 'zscore'
            ? 'zscore_remove'
            : 'iqr_remove';

    return {
        method,
        columns,
        threshold: Number(outlierThreshold.value),
    };
}

function buildTextStrategy() {
    const operations = Object.entries(textCleaningOptions.value)
        .filter(([, enabled]) => enabled)
        .map(([key]) => key);
    const method = operations.find((operation) => ['trim', 'lower', 'upper', 'title'].includes(operation)) ?? 'trim';

    return {
        method,
        columns: textColumnsSelected.value.length ? textColumnsSelected.value : textColumns.value,
        operations,
    };
}

function buildTypeStrategy() {
    return {
        casts: typeCastingSelections.value,
    };
}

function formatDetail(detail) {
    if (!detail) {
        return '';
    }

    const label = detail.column ?? detail.name ?? '-';
    const suffix = detail.missing_count ? ` (${detail.missing_count})` : '';
    return `${label}${suffix}`;
}

function missingValueForColumn(columnName) {
    const detail = missingColumnDetails.value.find((item) => item.column === columnName);
    return missingCustomValues.value[columnName] ?? detail?.recommended_custom_value ?? 'Unknown';
}

function setMissingValueForColumn(columnName, value) {
    missingCustomValues.value = {
        ...missingCustomValues.value,
        [columnName]: value,
    };
}

function toggleSelection(list, item) {
    const index = list.value.indexOf(item);
    if (index === -1) {
        list.value.push(item);
    } else {
        list.value.splice(index, 1);
    }
}

function filterIssues(items) {
    return (items ?? []).filter((issue) => Number(issue?.count ?? 0) > 0);
}

function resetStrategies() {
    if (datasetStore.selectedId) {
        fetchCleaningData(datasetStore.selectedId);
    } else {
        setDefaultState();
    }
}

async function fetchCleaningData(datasetId) {
    if (!datasetId) {
        setDefaultState();
        return;
    }

    isLoading.value = true;
    try {
        const response = await api.cleaning.show(datasetId);
        const data = response.data;

        issues.value = filterIssues(data.issues);
        strategies.value = data.strategies ?? [];
        impact.value = normalizeImpact(data.impact);
        preview.value = data.preview ?? { before: null, after: null };
        initMissingMethods();
        prepareMissingValues(data.missing_columns ?? []);
        duplicateSubset.value = [];
        duplicateKeep.value = 'keep_first';
        outlierMethod.value = 'iqr';
        outlierAction.value = 'drop';
        outlierThreshold.value = 1.5;
        outlierColumns.value = numericColumns.value.slice();
        textColumnsSelected.value = textColumns.value.slice();
        initTypeCasting();
        cleaningResult.value = null;
    } catch (error) {
        toast.push(error.message, 'warning');
    } finally {
        isLoading.value = false;
    }
}

async function applyCleaning() {
    if (!datasetStore.selectedId || actionsLocked.value) {
        return;
    }

    const customColumns = missingColumnDetails.value.filter(
        (detail) => missingColumnMethods.value[detail.column] === 'custom_value',
    );

    if (customColumns.some((detail) => !String(missingCustomValues.value[detail.column] ?? '').trim())) {
        toast.push('Nilai kustom untuk semua kolom custom value harus diisi.', 'warning');
        return;
    }

    isApplying.value = true;
    try {
        const response = await api.cleaning.apply(datasetStore.selectedId, {
            strategies: {
                missing: buildMissingStrategy(),
                duplicate: buildDuplicateStrategy(),
                outlier: buildOutlierStrategy(),
                text: buildTextStrategy(),
                type_cast: buildTypeStrategy(),
                apply_to_problematic: true,
            },
        });

        const data = response.data;
        cleaningResult.value = data;
        impact.value = normalizeImpact(data.impact ?? impact.value);
        preview.value = data.preview ?? preview.value;
        await nextTick();
        toast.push('Cleaning selesai diterapkan pada salinan dataset.');
    } catch (error) {
        toast.push(error.message, 'warning');
    } finally {
        isApplying.value = false;
    }
}

function exportAudit() {
    downloadCsv('audit_cleaning.csv', ['Metrik', 'Nilai'], buildAuditRows(cleaningResult.value));
    toast.push('Audit log diunduh sebagai CSV.');
}

async function downloadCleaned() {
    if (!datasetStore.selectedId || actionsLocked.value) {
        return;
    }

    try {
        const response = await fetch(api.cleaning.downloadUrl(datasetStore.selectedId), {
            credentials: 'same-origin',
        });

        if (!response.ok) {
            let message = 'Hasil cleaning belum tersedia.';
            try {
                const payload = await response.json();
                message = payload.message ?? message;
            } catch {
                // ignore
            }
            openDownloadDialog(message);
            return;
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        const datasetName = datasetStore.selected?.name?.replace(/[\\/:*?"<>|]/g, '_') ?? String(datasetStore.selectedId);

        link.href = url;
        link.download = `${datasetName}-cleaned.csv`;
        link.click();
        URL.revokeObjectURL(url);
    } catch (error) {
        openDownloadDialog(error.message);
    }
}

function openDownloadDialog(message) {
    downloadDialogMessage.value = message;
    downloadDialogOpen.value = true;
}

function closeDownloadDialog() {
    downloadDialogOpen.value = false;
    downloadDialogMessage.value = '';
}

watch(
    () => selectedDatasetId.value,
    (id) => {
        if (isApplying.value) {
            return;
        }

        if (id) {
            fetchCleaningData(id);
        } else {
            setDefaultState();
        }
    },
    { immediate: true },
);

watch(
    () => allColumns.value,
    () => {
        outlierColumns.value = numericColumns.value.slice();
        textColumnsSelected.value = textColumns.value.slice();
        initTypeCasting();
    },
    { immediate: true },
);

watch(
    () => missingColumnDetails.value,
    () => {
        initMissingMethods();
        prepareMissingValues(missingColumnDetails.value);
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
            <DatasetSelector :disabled="actionsLocked" />
            <AppButton
                icon="download"
                :disabled="actionsLocked || !issues.length || !datasetStore.selectedId"
                @click="downloadCleaned"
            >
                Unduh Hasil
            </AppButton>
            <AppButton
                variant="primary"
                icon="play"
                :disabled="actionsLocked ||!issues.length || !datasetStore.selectedId"
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
        <div v-if="issues.length" class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
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
                    <span class="text-3xl font-semibold leading-none text-ink dark:text-ink-dark">
                        {{ issue.count?.toLocaleString('id-ID') || 0 }}
                    </span>
                    <span class="text-sm text-ink-2 dark:text-ink-2-dark">
                        {{ issue.unit }}
                    </span>
                </p>

                <p class="mt-2 text-xs text-ink-2 dark:text-ink-2-dark">
                    {{ issue.description }}
                </p>

                <p v-if="issue.hint" class="mt-2 text-xs font-medium text-ink dark:text-ink-dark">
                    {{ issue.hint }}
                </p>

                <p v-if="issue.details?.length" class="mt-2 text-[11px] leading-5 text-ink-2 dark:text-ink-2-dark">
                    <span class="font-medium text-ink dark:text-ink-dark">Detail:</span>
                    {{ issue.details.map(formatDetail).join(' · ') }}
                </p>
            </div>
        </div>

        <div v-else class="mt-4">
            <AppCard flush>
                <EmptyState
                    icon="check"
                    title="Tidak ada masalah cleaning"
                    description="Dataset ini tidak memiliki issue yang perlu ditangani saat ini."
                />
            </AppCard>
        </div>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div class="lg:col-span-2">
                <AppCard
                    title="Strategi Pembersihan"
                    subtitle="Pilih modul cleaning dan sesuaikan opsi per kolom."
                >
                    <div class="space-y-4">
                        <div class="flex flex-wrap gap-2">
                            <button
                                v-for="tab in tabOptions"
                                :key="tab.key"
                                type="button"
                                :disabled="actionsLocked || !issues.length || !datasetStore.selectedId"
                                @click="activeTab = tab.key"
                                :class="activeTab === tab.key
                                    ? 'rounded-full bg-accent px-4 py-2 text-xs font-semibold text-white shadow-sm dark:bg-accent-dark'
                                    : 'rounded-full border border-hairline bg-surface px-4 py-2 text-xs font-medium text-ink hover:bg-plane dark:border-hairline-dark dark:bg-surface-dark dark:text-ink-dark dark:hover:bg-raised-dark'"
                            >
                                {{ tab.label }}
                            </button>
                        </div>

                        <div class="rounded-2xl border border-hairline bg-surface p-4 dark:border-hairline-dark dark:bg-surface-dark">
                            <div v-if="activeTab === 'missing'">
                                <p class="mb-4 text-sm font-medium text-ink dark:text-ink-dark">Handling nilai kosong per kolom.</p>
                                <div v-if="missingColumnDetails.length" class="space-y-4">
                                    <div
                                        v-for="detail in missingColumnDetails"
                                        :key="detail.column"
                                        class="rounded-2xl border border-hairline bg-plane p-4 dark:border-hairline-dark dark:bg-raised-dark"
                                    >
                                        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                            <div>
                                                <p class="text-sm font-semibold text-ink dark:text-ink-dark">{{ detail.column }}</p>
                                                <p class="text-xs text-ink-2 dark:text-ink-2-dark">{{ detail.type }} · {{ detail.missing_count }} sel kosong</p>
                                            </div>
                                            <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
                                                <select
                                                    v-model="missingColumnMethods[detail.column]"
                                                    :disabled="actionsLocked"
                                                    class="focus-ring h-10 rounded-lg border border-hairline bg-surface px-3 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-surface-dark dark:text-ink-dark"
                                                >
                                                    <option
                                                        v-for="option in missingMethodOptions"
                                                        :key="option.value"
                                                        :value="option.value"
                                                    >
                                                        {{ option.label }}
                                                    </option>
                                                </select>
                                                <input
                                                    v-if="missingColumnMethods[detail.column] === 'custom_value'"
                                                    v-model="missingCustomValues[detail.column]"
                                                    type="text"
                                                    :placeholder="detail.recommended_custom_value"
                                                    :disabled="actionsLocked"
                                                    class="focus-ring h-10 rounded-lg border border-hairline bg-surface px-3 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-surface-dark dark:text-ink-dark"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <EmptyState
                                    v-else
                                    icon="check"
            
                                    title="Tidak ada missing values"
                                    description="Dataset ini tidak memiliki sel kosong yang terdeteksi untuk kini."
                                />
                            </div>

                            <div v-if="activeTab === 'duplicate'">
                                <p class="mb-4 text-sm font-medium text-ink dark:text-ink-dark">Pilih kolom acuan dan aturan penyimpanan duplikat.</p>
                                <div class="grid gap-4 sm:grid-cols-2">
                                    <div class="rounded-2xl border border-hairline bg-plane p-4 dark:border-hairline-dark dark:bg-raised-dark">
                                        <p class="mb-3 text-sm font-semibold text-ink dark:text-ink-dark">Subset Columns</p>
                                        <div class="space-y-2 max-h-64 overflow-auto pr-1">
                                            <label
                                                v-for="column in (duplicateColumnDetails.length ? duplicateColumnDetails : comparableColumns)"
                                                :key="column"
                                                class="flex items-center gap-2 text-sm text-ink dark:text-ink-dark"
                                            >
                                                <input
                                                    type="checkbox"
                                                    :value="column"
                                                    :checked="duplicateSubset.includes(column)"
                                                    :disabled="actionsLocked"
                                                    @change="toggleSelection(duplicateSubset, column)"
                                                    class="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                                                />
                                                {{ column }}
                                            </label>
                                        </div>
                                        <p class="mt-3 text-xs text-ink-2 dark:text-ink-2-dark">Jika kosong, semua kolom non-identitas digunakan.</p>
                                    </div>

                                    <div class="rounded-2xl border border-hairline bg-plane p-4 dark:border-hairline-dark dark:bg-raised-dark">
                                        <p class="mb-3 text-sm font-semibold text-ink dark:text-ink-dark">Keep Rule</p>
                                        <div class="space-y-2">
                                            <label
                                                v-for="option in duplicateKeepOptions"
                                                :key="option.value"
                                                class="flex items-center gap-3 text-sm text-ink dark:text-ink-dark"
                                            >
                                                <input
                                                    type="radio"
                                                    name="duplicate-keep"
                                                    :value="option.value"
                                                    v-model="duplicateKeep"
                                                    :disabled="actionsLocked"
                                                    class="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                                                />
                                                {{ option.label }}
                                            </label>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div v-if="activeTab === 'outlier'">
                                <p class="mb-4 text-sm font-medium text-ink dark:text-ink-dark">Atur metode dan target kolom untuk penanganan outlier.</p>
                                <div class="grid gap-4 sm:grid-cols-2">
                                    <div class="rounded-2xl border border-hairline bg-plane p-4 dark:border-hairline-dark dark:bg-raised-dark">
                                        <p class="mb-3 text-sm font-semibold text-ink dark:text-ink-dark">Metode Deteksi</p>
                                        <div class="space-y-2">
                                            <label
                                                v-for="option in outlierMethodOptions"
                                                :key="option.value"
                                                class="flex items-center gap-3 text-sm text-ink dark:text-ink-dark"
                                            >
                                                <input
                                                    type="radio"
                                                    name="outlier-method"
                                                    :value="option.value"
                                                    v-model="outlierMethod"
                                                    :disabled="actionsLocked"
                                                    class="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                                                />
                                                {{ option.label }}
                                            </label>
                                        </div>
                                        <div class="mt-4 space-y-2">
                                            <label class="block text-sm font-medium text-ink dark:text-ink-dark">Threshold</label>
                                            <div class="flex items-center gap-3">
                                                <input
                                                    type="range"
                                                    min="0.5"
                                                    max="5"
                                                    step="0.1"
                                                    v-model.number="outlierThreshold"
                                                    :disabled="actionsLocked"
                                                    class="h-2 w-full cursor-pointer accent-accent"
                                                />
                                                <span class="w-14 text-right text-sm text-ink-2 dark:text-ink-2-dark">{{ outlierThreshold.toFixed(1) }}</span>
                                            </div>
                                            <input
                                                type="number"
                                                step="0.1"
                                                min="0.5"
                                                max="10"
                                                v-model.number="outlierThreshold"
                                                :disabled="actionsLocked"
                                                class="focus-ring h-10 w-full rounded-lg border border-hairline bg-surface px-3 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-surface-dark dark:text-ink-dark"
                                            />
                                        </div>
                                    </div>

                                    <div class="rounded-2xl border border-hairline bg-plane p-4 dark:border-hairline-dark dark:bg-raised-dark">
                                        <p class="mb-3 text-sm font-semibold text-ink dark:text-ink-dark">Aksi</p>
                                        <div class="space-y-2">
                                            <label
                                                v-for="option in outlierActionOptions"
                                                :key="option.value"
                                                class="flex items-center gap-3 text-sm text-ink dark:text-ink-dark"
                                            >
                                                <input
                                                    type="radio"
                                                    name="outlier-action"
                                                    :value="option.value"
                                                    v-model="outlierAction"
                                                    :disabled="actionsLocked"
                                                    class="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                                                />
                                                {{ option.label }}
                                            </label>
                                        </div>
                                    </div>
                                </div>

                                <div class="mt-4 rounded-2xl border border-hairline bg-plane p-4 dark:border-hairline-dark dark:bg-raised-dark">
                                    <p class="mb-3 text-sm font-semibold text-ink dark:text-ink-dark">Kolom Numerik</p>
                                    <div class="grid gap-2 sm:grid-cols-2">
                                        <label
                                            v-for="column in numericColumns"
                                            :key="column"
                                            class="flex items-center gap-2 text-sm text-ink dark:text-ink-dark"
                                        >
                                            <input
                                                type="checkbox"
                                                :value="column"
                                                :checked="outlierColumns.includes(column)"
                                                :disabled="actionsLocked"
                                                @change="toggleSelection(outlierColumns, column)"
                                                class="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                                            />
                                            {{ column }}
                                        </label>
                                    </div>
                                    <p class="mt-3 text-xs text-ink-2 dark:text-ink-2-dark">Jika tidak ada yang dipilih, semua kolom numerik digunakan.</p>
                                </div>
                            </div>

                            <div v-if="activeTab === 'text'">
                                <p class="mb-4 text-sm font-medium text-ink dark:text-ink-dark">Pilih transformasi teks dan target kolom.</p>
                                <div class="grid gap-4 sm:grid-cols-2">
                                    <div class="rounded-2xl border border-hairline bg-plane p-4 dark:border-hairline-dark dark:bg-raised-dark">
                                        <p class="mb-3 text-sm font-semibold text-ink dark:text-ink-dark">Operasi Teks</p>
                                        <div class="space-y-2">
                                            <label
                                                v-for="option in textCleaningOptionsList"
                                                :key="option.key"
                                                class="flex items-center gap-2 text-sm text-ink dark:text-ink-dark"
                                            >
                                                <input
                                                    type="checkbox"
                                                    :value="option.key"
                                                    v-model="textCleaningOptions[option.key]"
                                                    :disabled="actionsLocked"
                                                    class="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                                                />
                                                {{ option.label }}
                                            </label>
                                        </div>
                                    </div>

                                    <div class="rounded-2xl border border-hairline bg-plane p-4 dark:border-hairline-dark dark:bg-raised-dark">
                                        <p class="mb-3 text-sm font-semibold text-ink dark:text-ink-dark">Kolom Target</p>
                                        <div class="grid gap-2 max-h-64 overflow-auto pr-1">
                                            <label
                                                v-for="column in (textColumnDetails.length ? textColumnDetails : textColumns)"
                                                :key="column"
                                                class="flex items-center gap-2 text-sm text-ink dark:text-ink-dark"
                                            >
                                                <input
                                                    type="checkbox"
                                                    :value="column"
                                                    :checked="textColumnsSelected.includes(column)"
                                                    :disabled="actionsLocked"
                                                    @change="toggleSelection(textColumnsSelected, column)"
                                                    class="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                                                />
                                                {{ column }}
                                            </label>
                                        </div>
                                        <p class="mt-3 text-xs text-ink-2 dark:text-ink-2-dark">Kosongkan jika ingin menerapkan ke semua kolom teks yang tersedia.</p>
                                    </div>
                                </div>
                            </div>

                            <div v-if="activeTab === 'type'">
                                <p class="mb-4 text-sm font-medium text-ink dark:text-ink-dark">Konversi tipe data kolom dataset.</p>
                                <div class="overflow-auto">
                                    <table class="min-w-full border-separate border-spacing-0 text-sm">
                                        <thead>
                                            <tr>
                                                <th class="border-b border-hairline px-3 py-2 text-left font-medium text-ink-2 dark:border-hairline-dark dark:text-ink-2-dark">Kolom</th>
                                                <th class="border-b border-hairline px-3 py-2 text-left font-medium text-ink-2 dark:border-hairline-dark dark:text-ink-2-dark">Tipe Saat Ini</th>
                                                <th class="border-b border-hairline px-3 py-2 text-left font-medium text-ink-2 dark:border-hairline-dark dark:text-ink-2-dark">Target</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr
                                                v-for="column in allColumns"
                                                :key="column.name"
                                                class="border-b border-hairline last:border-0 dark:border-hairline-dark"
                                            >
                                                <td class="px-3 py-2 text-ink dark:text-ink-dark">{{ column.name }}</td>
                                                <td class="px-3 py-2 text-ink-2 dark:text-ink-2-dark">{{ column.type ?? 'unknown' }}</td>
                                                <td class="px-3 py-2">
                                                    <select
                                                        v-model="typeCastingSelections[column.name]"
                                                        :disabled="actionsLocked"
                                                        class="focus-ring h-9 w-full rounded-lg border border-hairline bg-surface px-3 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-surface-dark dark:text-ink-dark"
                                                    >
                                                        <option
                                                            v-for="option in typeCastingOptions"
                                                            :key="option.value"
                                                            :value="option.value"
                                                        >
                                                            {{ option.label }}
                                                        </option>
                                                    </select>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>

                    <template #footer>
                        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <p class="text-xs text-ink-3">Perubahan diterapkan pada salinan dataset; dataset asli tetap utuh.</p>
                            <div class="flex flex-wrap gap-2">
                                <AppButton size="sm" icon="download" :disabled="actionsLocked || !issues.length || !datasetStore.selectedId" @click="exportAudit">Audit Log</AppButton>
                                <AppButton size="sm" icon="refresh" @click="resetStrategies">Kembalikan Default</AppButton>
                            </div>
                        </div>
                    </template>
                </AppCard>
            </div>

            <ChartPanel
                class="self-start"
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

        <div class="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
            <AppCard title="Preview Sebelum" subtitle="10 baris awal dataset aktif">
                <div v-if="previewColumns(preview.before).length" class="overflow-auto">
                    <table class="min-w-full border-separate border-spacing-0 text-sm">
                        <thead>
                            <tr>
                                <th
                                    v-for="column in previewColumns(preview.before)"
                                    :key="column"
                                    class="border-b border-hairline px-3 py-2 text-left font-medium text-ink-2 dark:border-hairline-dark dark:text-ink-2-dark"
                                >
                                    {{ column }}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(row, rowIndex) in previewRows(preview.before)" :key="rowIndex">
                                <td
                                    v-for="(cell, cellIndex) in row"
                                    :key="rowIndex + '-' + cellIndex"
                                    class="border-b border-hairline px-3 py-2 text-ink dark:border-hairline-dark dark:text-ink-dark"
                                >
                                    {{ cell }}
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <EmptyState
                    v-else
                    icon="check"
                    title="Preview belum tersedia"
                    description="Dataset belum memiliki cuplikan yang bisa ditampilkan."
                />
            </AppCard>

            <AppCard title="Preview Sesudah" subtitle="Hasil sementara dari strategi aktif">
                <div v-if="previewColumns(preview.after).length" class="overflow-auto">
                    <table class="min-w-full border-separate border-spacing-0 text-sm">
                        <thead>
                            <tr>
                                <th
                                    v-for="column in previewColumns(preview.after)"
                                    :key="column"
                                    class="border-b border-hairline px-3 py-2 text-left font-medium text-ink-2 dark:border-hairline-dark dark:text-ink-2-dark"
                                >
                                    {{ column }}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(row, rowIndex) in previewRows(preview.after)" :key="rowIndex">
                                <td
                                    v-for="(cell, cellIndex) in row"
                                    :key="rowIndex + '-' + cellIndex"
                                    :class="[
                                        'border-b border-hairline px-3 py-2 text-ink dark:border-hairline-dark dark:text-ink-dark',
                                        previewCellChanged(rowIndex, cellIndex)
                                            ? 'bg-amber-100/70 dark:bg-amber-500/10'
                                            : '',
                                    ]"
                                >
                                    {{ cell }}
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <EmptyState
                    v-else
                    icon="profiling"
                    title="Jalankan cleaning"
                    description="Hasil sesudah akan tampil setelah strategi diterapkan."
                />
            </AppCard>
        </div>
    </template>

    <Transition
        enter-active-class="transition-opacity ease-out duration-150"
        enter-from-class="opacity-0"
        leave-active-class="transition-opacity ease-in duration-100"
        leave-to-class="opacity-0"
    >
        <div
            v-if="downloadDialogOpen"
            class="fixed inset-0 z-[80] flex items-center justify-center p-4"
        >
            <div
                class="absolute inset-0 bg-ink/40"
                @click="closeDownloadDialog"
            />

            <div
                role="dialog"
                aria-modal="true"
                aria-label="Hasil cleaning belum tersedia"
                class="relative w-full max-w-sm rounded-xl border border-hairline bg-surface p-5 shadow-xl dark:border-hairline-dark dark:bg-surface-dark"
            >
                <h2 class="text-sm font-semibold text-ink dark:text-ink-dark">
                    Hasil cleaning belum tersedia
                </h2>
                <p class="mt-2 text-sm text-ink-2 dark:text-ink-2-dark">
                    {{ downloadDialogMessage }}
                </p>

                <div class="mt-5 flex justify-end">
                    <AppButton variant="primary" @click="closeDownloadDialog">
                        Tutup
                    </AppButton>
                </div>
            </div>
        </div>
    </Transition>
</template>
