<script setup>
import { computed, ref } from 'vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import StatusBadge from '@/Components/UI/StatusBadge.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useToastStore } from '@/stores/toast';
import { useConfirmStore } from '@/stores/confirm';
import { downloadText } from '@/Utils/exportCsv';
import { reports } from '@/data/placeholder';

const TEMPLATES = [
    {
        name: 'Laporan Profiling',
        icon: 'profiling',
        type: 'Profiling',
        description: 'Ringkasan struktur, kelengkapan, dan sebaran seluruh kolom.',
    },
    {
        name: 'Laporan Cleaning',
        icon: 'cleaning',
        type: 'Cleaning',
        description: 'Catatan setiap langkah pembersihan beserta dampaknya.',
    },
    {
        name: 'Laporan Data Mining',
        icon: 'mining',
        type: 'Data Mining',
        description: 'Hasil clustering, association rule, dan deteksi anomali.',
    },
    {
        name: 'Laporan Model',
        icon: 'ml',
        type: 'Machine Learning',
        description: 'Metrik evaluasi, feature importance, dan confusion matrix.',
    },
];

const datasetStore = useDatasetStore();
const toast = useToastStore();
const confirm = useConfirmStore();

// Salinan lokal agar aksi buat/hapus tidak memutasi data sumber bersama.
const reportList = ref(reports.map((report) => ({ ...report })));

/*
 * Laporan selalu terikat pada satu dataset, jadi daftarnya disaring mengikuti
 * dataset aktif — sama seperti halaman analisis lain. "Semua dataset" tetap
 * disediakan karena laporan lama tetap perlu ditemukan tanpa berpindah pilihan.
 */
const scope = ref('selected');

const visibleReports = computed(() =>
    scope.value === 'all'
        ? reportList.value
        : reportList.value.filter(
              (report) => report.dataset === datasetStore.selected?.name,
          ),
);

// Simulasi penyusunan laporan; nanti diganti job asli dari backend.
function createReport(template = null) {
    const id = Math.max(0, ...reportList.value.map((report) => report.id)) + 1;
    const datasetName = datasetStore.selected?.name ?? 'seluruh dataset';
    const title = template
        ? `${template.name} — ${datasetName}`
        : `Laporan Analisis — ${datasetName}`;

    reportList.value = [
        {
            id,
            title,
            dataset: datasetName,
            type: template?.type ?? 'Gabungan',
            format: 'PDF',
            size: '—',
            status: 'generating',
            created_at: new Date().toLocaleDateString('id-ID', {
                day: 'numeric',
                month: 'short',
                year: 'numeric',
            }),
        },
        ...reportList.value,
    ];

    toast.push(`"${title}" sedang disusun.`);

    setTimeout(() => {
        const saved = reportList.value.find((report) => report.id === id);

        if (saved) {
            saved.status = 'ready';
            saved.size = '1,2 MB';
            toast.push(`"${saved.title}" siap diunduh.`);
        }
    }, 4000);
}

async function removeReport(report) {
    const confirmed = await confirm.open({
        title: 'Hapus laporan',
        message: `Laporan "${report.title}" akan dihapus permanen.`,
    });

    if (!confirmed) {
        return;
    }

    reportList.value = reportList.value.filter((item) => item.id !== report.id);
    toast.push(`Laporan "${report.title}" dihapus.`);
}

function downloadReport(report) {
    // Dokumen PDF/XLSX asli baru bisa dibuat backend; sementara unduh ringkasan.
    downloadText(
        `${report.title}.txt`,
        [
            report.title,
            '='.repeat(report.title.length),
            '',
            `Dataset   : ${report.dataset}`,
            `Jenis     : ${report.type}`,
            `Format    : ${report.format}`,
            `Dibuat    : ${report.created_at}`,
            `Status    : ${report.status}`,
            '',
            'Dokumen lengkap tersedia setelah backend tersambung.',
        ].join('\n'),
    );
    toast.push('Ringkasan laporan diunduh — dokumen penuh menunggu backend.');
}

function previewReport(report) {
    toast.push(
        `Pratinjau "${report.title}" tersedia setelah backend tersambung.`,
        'warning',
    );
}
</script>

<template>
    <PageHeader
        title="Laporan"
        description="Hasil analisis yang dirangkum menjadi dokumen siap dibagikan."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Laporan' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
            <AppButton variant="primary" icon="plus" @click="createReport()">
                Buat Laporan
            </AppButton>
        </template>
    </PageHeader>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div class="space-y-3 lg:col-span-2">
            <!-- Cakupan daftar: dataset aktif saja, atau seluruh dataset -->
            <div class="flex flex-wrap items-center gap-3">
                <div
                    class="flex items-center gap-0.5 rounded-lg border border-hairline p-0.5 dark:border-hairline-dark"
                    role="group"
                    aria-label="Saring dataset"
                >
                    <button
                        v-for="option in [
                            { value: 'selected', label: 'Dataset terpilih' },
                            { value: 'all', label: 'Semua dataset' },
                        ]"
                        :key="option.value"
                        type="button"
                        class="focus-ring rounded-md px-2.5 py-1 text-xs font-medium transition-colors"
                        :class="
                            scope === option.value
                                ? 'bg-plane text-ink dark:bg-raised-dark dark:text-ink-dark'
                                : 'text-ink-3 hover:text-ink dark:hover:text-ink-dark'
                        "
                        :aria-pressed="scope === option.value"
                        @click="scope = option.value"
                    >
                        {{ option.label }}
                    </button>
                </div>

                <p class="ml-auto text-xs tabular-nums text-ink-3">
                    {{ visibleReports.length }} dari
                    {{ reportList.length }} laporan
                </p>
            </div>

            <AppCard v-if="visibleReports.length === 0" flush>
                <EmptyState
                    icon="reports"
                    :title="
                        reportList.length === 0
                            ? 'Belum ada laporan'
                            : 'Belum ada laporan untuk dataset ini'
                    "
                    :description="
                        reportList.length === 0
                            ? 'Buat laporan baru dari tombol di atas atau pilih salah satu template.'
                            : `Belum ada laporan yang dibuat dari ${datasetStore.selected?.name ?? 'dataset ini'}. Pilih dataset lain, atau lihat semua dataset.`
                    "
                >
                    <template #action>
                        <AppButton
                            variant="primary"
                            icon="plus"
                            @click="createReport()"
                        >
                            Buat Laporan
                        </AppButton>
                    </template>
                </EmptyState>
            </AppCard>

            <article
                v-for="report in visibleReports"
                :key="report.id"
                class="flex flex-wrap items-center gap-4 rounded-xl border border-hairline bg-surface p-4 transition-colors hover:bg-plane dark:border-hairline-dark dark:bg-surface-dark dark:hover:bg-raised-dark/60"
            >
                <span
                    class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-plane text-ink-3 dark:bg-raised-dark"
                >
                    <AppIcon name="document" class="h-5 w-5" />
                </span>

                <div class="min-w-0 flex-1">
                    <p class="truncate text-sm font-medium text-ink dark:text-ink-dark">
                        {{ report.title }}
                    </p>
                    <p class="mt-0.5 truncate text-xs text-ink-3">
                        {{ report.dataset }} · {{ report.created_at }} ·
                        {{ report.size }}
                    </p>
                </div>

                <div class="flex shrink-0 items-center gap-2">
                    <AppBadge>{{ report.type }}</AppBadge>
                    <AppBadge>{{ report.format }}</AppBadge>
                    <StatusBadge :status="report.status" />
                </div>

                <div class="flex shrink-0 items-center gap-1">
                    <button
                        type="button"
                        class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-ink dark:hover:text-ink-dark"
                        title="Pratinjau"
                        :disabled="report.status !== 'ready'"
                        :class="report.status !== 'ready' ? 'opacity-40' : ''"
                        @click="previewReport(report)"
                    >
                        <AppIcon name="eye" class="h-4 w-4" />
                        <span class="sr-only">Pratinjau {{ report.title }}</span>
                    </button>
                    <button
                        type="button"
                        class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-ink dark:hover:text-ink-dark"
                        title="Unduh"
                        :disabled="report.status !== 'ready'"
                        :class="report.status !== 'ready' ? 'opacity-40' : ''"
                        @click="downloadReport(report)"
                    >
                        <AppIcon name="download" class="h-4 w-4" />
                        <span class="sr-only">Unduh {{ report.title }}</span>
                    </button>
                    <button
                        type="button"
                        class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-status-critical"
                        title="Hapus"
                        @click="removeReport(report)"
                    >
                        <AppIcon name="trash" class="h-4 w-4" />
                        <span class="sr-only">Hapus {{ report.title }}</span>
                    </button>
                </div>
            </article>
        </div>

        <AppCard title="Template Laporan" flush>
            <ul>
                <li
                    v-for="template in TEMPLATES"
                    :key="template.name"
                    class="border-b border-hairline last:border-0 dark:border-hairline-dark"
                >
                    <button
                        type="button"
                        class="focus-ring flex w-full gap-3 px-5 py-3.5 text-left transition-colors hover:bg-plane dark:hover:bg-raised-dark/60"
                        @click="createReport(template)"
                    >
                        <AppIcon
                            :name="template.icon"
                            class="mt-0.5 h-[18px] w-[18px] shrink-0 text-accent dark:text-accent-dark"
                        />
                        <div class="min-w-0">
                            <p class="text-sm font-medium text-ink dark:text-ink-dark">
                                {{ template.name }}
                            </p>
                            <p class="mt-0.5 text-xs text-ink-2 dark:text-ink-2-dark">
                                {{ template.description }}
                            </p>
                        </div>
                    </button>
                </li>
            </ul>
        </AppCard>
    </div>
</template>
