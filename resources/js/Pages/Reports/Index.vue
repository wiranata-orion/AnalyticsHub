<script setup>
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import StatusBadge from '@/Components/UI/StatusBadge.vue';
import { reports } from '@/data/placeholder';

const TEMPLATES = [
    {
        name: 'Laporan Profiling',
        icon: 'profiling',
        description: 'Ringkasan struktur, kelengkapan, dan sebaran seluruh kolom.',
    },
    {
        name: 'Laporan Cleaning',
        icon: 'cleaning',
        description: 'Catatan setiap langkah pembersihan beserta dampaknya.',
    },
    {
        name: 'Laporan Data Mining',
        icon: 'mining',
        description: 'Hasil clustering, association rule, dan deteksi anomali.',
    },
    {
        name: 'Laporan Model',
        icon: 'ml',
        description: 'Metrik evaluasi, feature importance, dan confusion matrix.',
    },
];
</script>

<template>
    <AppLayout>
        <PageHeader
            title="Laporan"
            description="Hasil analisis yang dirangkum menjadi dokumen siap dibagikan."
            :breadcrumbs="[
                { label: 'Dashboard', to: { name: 'dashboard' } },
                { label: 'Laporan' },
            ]"
        >
            <template #actions>
                <AppButton variant="primary" icon="plus">Buat Laporan</AppButton>
            </template>
        </PageHeader>

        <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div class="space-y-3 lg:col-span-2">
                <article
                    v-for="report in reports"
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
                        >
                            <AppIcon name="eye" class="h-4 w-4" />
                        </button>
                        <button
                            type="button"
                            class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-ink dark:hover:text-ink-dark"
                            title="Unduh"
                            :disabled="report.status !== 'ready'"
                            :class="report.status !== 'ready' ? 'opacity-40' : ''"
                        >
                            <AppIcon name="download" class="h-4 w-4" />
                        </button>
                        <button
                            type="button"
                            class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-status-critical"
                            title="Hapus"
                        >
                            <AppIcon name="trash" class="h-4 w-4" />
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
    </AppLayout>
</template>
