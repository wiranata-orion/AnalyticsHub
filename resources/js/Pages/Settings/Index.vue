<script setup>
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import ThemeToggle from '@/Components/UI/ThemeToggle.vue';
import { useTheme } from '@/Composables/useTheme';

const { preference } = useTheme();

const THEME_LABELS = {
    light: 'Selalu terang',
    dark: 'Selalu gelap',
    system: 'Mengikuti pengaturan sistem',
};

const ENGINE_ROWS = [
    { label: 'Interpreter', value: 'python/venv/Scripts/python.exe' },
    { label: 'Skrip Entry', value: 'python/main.py' },
    { label: 'Batas Waktu Job', value: '600 detik' },
    { label: 'Maksimum Baris per Job', value: '5.000.000' },
];

const SYSTEM_ROWS = [
    { label: 'Versi Aplikasi', value: '0.1.0' },
    { label: 'Vue', value: '3.x' },
    { label: 'Vite', value: '8.x' },
    { label: 'REST API', value: 'belum tersambung' },
    { label: 'Python', value: 'belum tersambung' },
];
</script>

<template>
    <AppLayout>
        <PageHeader
            title="Pengaturan"
            description="Preferensi tampilan, engine analisis, dan penyimpanan data."
            :breadcrumbs="[
                { label: 'Dashboard', to: { name: 'dashboard' } },
                { label: 'Pengaturan' },
            ]"
        />

        <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div class="space-y-4 lg:col-span-2">
                <AppCard
                    title="Tampilan"
                    subtitle="Preferensi tema disimpan di peramban ini saja."
                >
                    <div class="flex flex-wrap items-center justify-between gap-4">
                        <div class="min-w-0">
                            <p class="text-sm font-medium text-ink dark:text-ink-dark">
                                Tema Antarmuka
                            </p>
                            <p class="mt-0.5 text-sm text-ink-2 dark:text-ink-2-dark">
                                {{ THEME_LABELS[preference] }}
                            </p>
                        </div>

                        <ThemeToggle />
                    </div>
                </AppCard>

                <AppCard
                    title="Python Engine"
                    subtitle="Konfigurasi proses yang menjalankan analisis."
                >
                    <dl class="space-y-3.5">
                        <div
                            v-for="row in ENGINE_ROWS"
                            :key="row.label"
                            class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-hairline pb-3.5 last:border-0 last:pb-0 dark:border-hairline-dark"
                        >
                            <dt class="text-sm text-ink-2 dark:text-ink-2-dark">
                                {{ row.label }}
                            </dt>
                            <dd class="font-mono text-xs text-ink dark:text-ink-dark">
                                {{ row.value }}
                            </dd>
                        </div>
                    </dl>

                    <template #footer>
                        <div class="flex items-center gap-2">
                            <AppIcon
                                name="warning"
                                class="h-4 w-4 shrink-0 text-[#8a5a00] dark:text-status-warning"
                            />
                            <p class="text-xs text-ink-2 dark:text-ink-2-dark">
                                Backend belum tersambung — nilai di atas masih
                                placeholder.
                            </p>
                        </div>
                    </template>
                </AppCard>

                <AppCard
                    title="Penyimpanan Dataset"
                    subtitle="Aturan retensi berkas yang diunggah."
                >
                    <div class="space-y-4">
                        <label
                            v-for="option in [
                                {
                                    label: 'Simpan berkas asli setelah cleaning selesai',
                                    checked: true,
                                },
                                {
                                    label: 'Hapus otomatis dataset yang tidak diakses 90 hari',
                                    checked: false,
                                },
                                {
                                    label: 'Kirim notifikasi saat analisis selesai',
                                    checked: true,
                                },
                            ]"
                            :key="option.label"
                            class="flex items-start gap-2.5"
                        >
                            <input
                                type="checkbox"
                                :checked="option.checked"
                                class="focus-ring mt-0.5 h-4 w-4 rounded border-hairline text-accent focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark"
                            />
                            <span class="text-sm text-ink-2 dark:text-ink-2-dark">
                                {{ option.label }}
                            </span>
                        </label>
                    </div>

                    <template #footer>
                        <div class="flex justify-end">
                            <AppButton variant="primary" size="sm">
                                Simpan Perubahan
                            </AppButton>
                        </div>
                    </template>
                </AppCard>
            </div>

            <AppCard title="Informasi Sistem">
                <dl class="space-y-3">
                    <div
                        v-for="row in SYSTEM_ROWS"
                        :key="row.label"
                        class="flex items-center justify-between gap-3"
                    >
                        <dt class="text-sm text-ink-2 dark:text-ink-2-dark">
                            {{ row.label }}
                        </dt>
                        <dd>
                            <AppBadge
                                :variant="
                                    row.value === 'belum tersambung'
                                        ? 'warning'
                                        : 'neutral'
                                "
                            >
                                {{ row.value }}
                            </AppBadge>
                        </dd>
                    </div>
                </dl>
            </AppCard>
        </div>
    </AppLayout>
</template>
