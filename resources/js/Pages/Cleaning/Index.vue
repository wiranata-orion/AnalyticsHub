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
const selectedStrategies = ref({});
const missingCustomValue = ref('Unknown');
const cleaningResult = ref(null);

const isLoading = ref(false);
const isApplying = ref(false);
const downloadDialogOpen = ref(false);
const downloadDialogMessage = ref('');

const selectedDatasetId = computed(() => datasetStore.selectedId);
const actionsLocked = computed(() => isLoading.value || isApplying.value || datasetStore.isLoading);

const ISSUE_TONES = {
    warning: 'text-[#8a5a00] dark:text-status-warning',
    serious: 'text-[#a34418] dark:text-status-serious',
    critical: 'text-status-critical',
};

const defaultStrategies = () =>
    Object.fromEntries(
        strategies.value.map((strategy) => [strategy.key, strategy.selected]),
    );

const previewColumns = (view) => view?.columns ?? [];

const previewRows = (view) => view?.rows ?? [];

const issueDetails = (issue) => issue?.details ?? [];
const missingColumnDetails = computed(() => issues.value.find((issue) => issue.key === 'missing')?.details ?? []);
const missingCustomValues = ref({});

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

function filterIssues(items) {
    return (items ?? []).filter((issue) => Number(issue?.count ?? 0) > 0);
}

function buildIssuesFromResult(data) {
    return filterIssues(data.issues);
}

function missingCustomHint(strategy) {
    if (strategy?.key !== 'missing') {
        return '';
    }

    return strategy?.hint ?? '';
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

function prepareMissingValues(details) {
    const prepared = {};

    (details ?? []).forEach((detail) => {
        if (detail?.column) {
            prepared[detail.column] = detail.recommended_custom_value ?? 'Unknown';
        }
    });

    missingCustomValues.value = prepared;
}

function normalizeSelectedStrategies() {
    if (!strategies.value.length) {
        return;
    }

    const defaults = defaultStrategies();
    selectedStrategies.value = {
        ...defaults,
        ...selectedStrategies.value,
    };
}

function setDefaultState() {
    issues.value = [];
    strategies.value = [];
    impact.value = { labels: [], series: [] };
    preview.value = { before: null, after: null };
    selectedStrategies.value = {};
    missingCustomValue.value = 'Unknown';
    missingCustomValues.value = {};
    cleaningResult.value = null;
}

function buildAuditRows(result) {
    const rowsBefore = result?.impact?.rows?.[0] ?? datasetStore.selectedDetail?.rows ?? '—';
    const rowsAfter = result?.impact?.rows?.[1] ?? '—';
    const missingStrategyLabel = selectedStrategies.value.missing === 'custom_value'
        ? `custom_value (${missingCustomValue.value || '—'})`
        : selectedStrategies.value.missing ?? '—';

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
        ['Strategi Missing', missingStrategyLabel],
        ['Strategi Duplikat', selectedStrategies.value.duplicate ?? '—'],
        ['Strategi Outlier', selectedStrategies.value.outlier ?? '—'],
        ['Strategi Teks', selectedStrategies.value.text ?? '—'],
    ];
}

function openDownloadDialog(message) {
    downloadDialogMessage.value = message;
    downloadDialogOpen.value = true;
}

function closeDownloadDialog() {
    downloadDialogOpen.value = false;
    downloadDialogMessage.value = '';
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
        selectedStrategies.value = data.selected ?? {};
        prepareMissingValues(data.missing_columns ?? issues.value.find((issue) => issue.key === 'missing')?.details);
        cleaningResult.value = null;
        normalizeSelectedStrategies();
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

    if (selectedStrategies.value.missing === 'custom_value' && !String(missingCustomValue.value ?? '').trim()) {
        const hasAnyCustomValue = Object.values(missingCustomValues.value).some((value) => String(value ?? '').trim().length > 0);

        if (!hasAnyCustomValue) {
            toast.push('Nilai kustom untuk missing value harus diisi.', 'warning');
            return;
        }
    }

    isApplying.value = true;
    try {
        const missingStrategy = selectedStrategies.value.missing === 'custom_value'
            ? {
                method: 'custom_value',
                custom_values: Object.fromEntries(
                    Object.entries(missingCustomValues.value).filter(([, value]) => String(value ?? '').trim().length > 0),
                ),
            }
            : selectedStrategies.value.missing;

        const response = await api.cleaning.apply(datasetStore.selectedId, {
            strategies: {
                ...selectedStrategies.value,
                missing: missingStrategy,
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

function resetStrategies() {
    selectedStrategies.value = defaultStrategies();
    missingCustomValue.value = 'Unknown';
    prepareMissingValues(missingColumnDetails.value);
    toast.push('Strategi dikembalikan ke rekomendasi default.');
}

function exportAudit() {
    downloadCsv(
        'audit_cleaning.csv',
        ['Metrik', 'Nilai'],
        buildAuditRows(cleaningResult.value),
    );
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
                // Biarkan pesan default.
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
                :disabled="actionsLocked || !datasetStore.selectedId"
                @click="downloadCleaned"
            >
                Unduh Hasil
            </AppButton>
            <AppButton
                variant="primary"
                icon="play"
                :disabled="actionsLocked || !datasetStore.selectedId"
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

                <p v-if="issueDetails(issue).length" class="mt-2 text-[11px] leading-5 text-ink-2 dark:text-ink-2-dark">
                    <span class="font-medium text-ink dark:text-ink-dark">Detail:</span>
                    {{ issueDetails(issue).map(formatDetail).join(' · ') }}
                </p>
            </div>
        </div>

        <AppCard v-else flush class="mt-4">
            <EmptyState
                icon="check"
                title="Tidak ada masalah cleaning"
                description="Dataset ini tidak memiliki issue yang perlu ditangani saat ini."
            />
        </AppCard>

        <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div class="lg:col-span-2">
                <AppCard
                    title="Strategi Pembersihan"
                    subtitle="Pilihan ini menentukan langkah yang dijalankan Python engine."
                >
                    <div v-if="strategies.length" class="space-y-5">
                        <div
                            v-for="strategy in strategies"
                            :key="strategy.key"
                            class="border-b border-hairline pb-5 last:border-0 last:pb-0 dark:border-hairline-dark"
                        >
                            <p class="mb-2.5 text-sm font-medium text-ink dark:text-ink-dark">
                                {{ strategy.label }}
                            </p>

                            <p v-if="missingCustomHint(strategy)" class="mb-3 text-xs text-ink-2 dark:text-ink-2-dark">
                                {{ missingCustomHint(strategy) }}
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

                            <div
                                v-if="strategy.key === 'missing' && selectedStrategies[strategy.key] === 'custom_value'"
                                class="mt-3 space-y-3"
                            >
                                <p class="text-xs text-ink-2 dark:text-ink-2-dark">
                                    Isi nilai pengganti per kolom agar teks dan numerik tidak dipaksa memakai nilai yang sama.
                                </p>

                                <div v-if="missingColumnDetails.length" class="space-y-3">
                                    <div
                                        v-for="detail in missingColumnDetails"
                                        :key="detail.column"
                                        class="rounded-lg border border-hairline bg-plane/30 p-3 dark:border-hairline-dark dark:bg-raised-dark/20"
                                    >
                                        <div class="flex items-start justify-between gap-3">
                                            <div>
                                                <p class="text-sm font-medium text-ink dark:text-ink-dark">
                                                    {{ detail.column }}
                                                </p>
                                                <p class="text-xs text-ink-2 dark:text-ink-2-dark">
                                                    {{ detail.type }} · {{ detail.missing_count }} sel kosong
                                                </p>
                                                <p class="mt-1 text-[11px] text-ink-2 dark:text-ink-2-dark">
                                                    Saran: {{ detail.recommended_strategy }} / {{ detail.recommended_custom_value }}
                                                </p>
                                            </div>
                                            <input
                                                :value="missingValueForColumn(detail.column)"
                                                type="text"
                                                :placeholder="detail.recommended_custom_value"
                                                :disabled="actionsLocked"
                                                class="focus-ring h-9 w-40 rounded-lg border-hairline bg-surface px-3 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-surface-dark dark:text-ink-dark"
                                                @input="setMissingValueForColumn(detail.column, $event.target.value)"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <p class="text-[11px] text-ink-2 dark:text-ink-2-dark">
                                    Nilai numerik sebaiknya tetap numerik, sedangkan kolom teks/kategori biasanya lebih aman diisi dengan label seperti Unknown atau Tidak Diketahui.
                                </p>
                            </div>
                        </div>
                    </div>
                    <EmptyState
                        v-else
                        icon="check"
                        title="Tidak ada strategi yang perlu dijalankan"
                        description="Semua bagian dataset sudah bersih dari masalah yang didukung oleh engine saat ini."
                    />

                    <template #footer>
                        <div class="flex items-center justify-between gap-3">
                            <p class="text-xs text-ink-3">
                                Perubahan diterapkan pada salinan, dataset asli tetap utuh.
                            </p>
                            <div class="flex gap-2">
                                <AppButton size="sm" icon="download" @click="exportAudit">
                                    Audit Log
                                </AppButton>
                                <AppButton size="sm" icon="refresh" @click="resetStrategies">
                                    Kembalikan Default
                                </AppButton>
                            </div>
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
                                    :key="`${rowIndex}-${cellIndex}`"
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
                                    :key="`${rowIndex}-${cellIndex}`"
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