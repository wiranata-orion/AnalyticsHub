<script setup>
import { computed, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import AppIcon from '@/Components/UI/AppIcon.vue';
import SidebarLink from '@/Components/Navigation/SidebarLink.vue';
import ThemeToggle from '@/Components/UI/ThemeToggle.vue';

/*
 * Shell aplikasi: sidebar tetap di layar besar, drawer di layar kecil.
 *
 * Navigasi didefinisikan sebagai data, bukan markup berulang — menambah menu
 * cukup menambah satu entri. `match` adalah awalan nama rute, sehingga
 * `/datasets/create` tetap menyalakan menu "Dataset".
 */
const route = useRoute();
const sidebarOpen = ref(false);

const NAV_GROUPS = [
    {
        label: null,
        items: [
            { label: 'Dashboard', icon: 'dashboard', name: 'dashboard', match: 'dashboard' },
        ],
    },
    {
        label: 'Data',
        items: [
            { label: 'Dataset', icon: 'datasets', name: 'datasets.index', match: 'datasets' },
            { label: 'Profiling', icon: 'profiling', name: 'profiling.index', match: 'profiling' },
            { label: 'Cleaning', icon: 'cleaning', name: 'cleaning.index', match: 'cleaning' },
        ],
    },
    {
        label: 'Analisis',
        items: [
            { label: 'Visualisasi', icon: 'visualization', name: 'visualization.index', match: 'visualization' },
            { label: 'Data Mining', icon: 'mining', name: 'mining.index', match: 'mining' },
            { label: 'Machine Learning', icon: 'ml', name: 'machine-learning.index', match: 'machine-learning' },
        ],
    },
    {
        label: 'Keluaran',
        items: [
            { label: 'Laporan', icon: 'reports', name: 'reports.index', match: 'reports' },
        ],
    },
    {
        label: 'Sistem',
        items: [
            { label: 'Pengaturan', icon: 'settings', name: 'settings.index', match: 'settings' },
        ],
    },
];

const currentName = computed(() => String(route.name ?? ''));

const isActive = (match) =>
    currentName.value === match || currentName.value.startsWith(`${match}.`);

// Drawer ditutup otomatis setelah berpindah halaman di layar kecil.
watch(() => route.fullPath, () => (sidebarOpen.value = false));
</script>

<template>
    <div class="min-h-screen bg-plane dark:bg-plane-dark">
        <!-- Lapisan gelap drawer, hanya pada layar kecil -->
        <Transition
            enter-active-class="transition-opacity ease-out duration-200"
            enter-from-class="opacity-0"
            leave-active-class="transition-opacity ease-in duration-150"
            leave-to-class="opacity-0"
        >
            <div
                v-if="sidebarOpen"
                class="fixed inset-0 z-40 bg-ink/40 lg:hidden"
                @click="sidebarOpen = false"
            />
        </Transition>

        <!-- Sidebar -->
        <aside
            class="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-hairline bg-surface transition-transform duration-200 dark:border-hairline-dark dark:bg-surface-dark lg:translate-x-0"
            :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'"
        >
            <div
                class="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-hairline px-4 dark:border-hairline-dark"
            >
                <RouterLink
                    :to="{ name: 'dashboard' }"
                    class="focus-ring flex items-center gap-2 rounded-lg"
                >
                    <span
                        class="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-white dark:bg-accent-dark"
                    >
                        <AppIcon name="profiling" class="h-4 w-4" />
                    </span>
                    <span
                        class="text-sm font-semibold tracking-tight text-ink dark:text-ink-dark"
                    >
                        AnalyticsHub
                    </span>
                </RouterLink>

                <button
                    type="button"
                    class="focus-ring -mr-1 rounded-lg p-1.5 text-ink-3 hover:text-ink dark:hover:text-ink-dark lg:hidden"
                    @click="sidebarOpen = false"
                >
                    <AppIcon name="close" class="h-5 w-5" />
                    <span class="sr-only">Tutup navigasi</span>
                </button>
            </div>

            <nav class="flex-1 space-y-5 overflow-y-auto px-3 py-4">
                <div v-for="(group, index) in NAV_GROUPS" :key="index">
                    <p
                        v-if="group.label"
                        class="mb-1.5 px-3 text-[11px] font-medium uppercase tracking-wider text-ink-3"
                    >
                        {{ group.label }}
                    </p>

                    <div class="space-y-0.5">
                        <SidebarLink
                            v-for="item in group.items"
                            :key="item.name"
                            :to="{ name: item.name }"
                            :icon="item.icon"
                            :active="isActive(item.match)"
                        >
                            {{ item.label }}
                        </SidebarLink>
                    </div>
                </div>
            </nav>

            <div class="shrink-0 border-t border-hairline p-3 dark:border-hairline-dark">
                <RouterLink
                    :to="{ name: 'datasets.create' }"
                    class="focus-ring flex items-center justify-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-[#256abf] dark:bg-accent-dark dark:hover:bg-[#2a78d6]"
                >
                    <AppIcon name="upload" class="h-4 w-4" />
                    Upload Dataset
                </RouterLink>
            </div>
        </aside>

        <!-- Area konten -->
        <div class="lg:pl-64">
            <header
                class="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-hairline bg-surface/85 px-4 backdrop-blur dark:border-hairline-dark dark:bg-surface-dark/85 sm:px-6"
            >
                <button
                    type="button"
                    class="focus-ring -ml-1 rounded-lg p-1.5 text-ink-2 hover:text-ink dark:text-ink-2-dark dark:hover:text-ink-dark lg:hidden"
                    @click="sidebarOpen = true"
                >
                    <AppIcon name="menu" class="h-5 w-5" />
                    <span class="sr-only">Buka navigasi</span>
                </button>

                <!-- Pencarian global -->
                <div class="relative hidden max-w-xs flex-1 sm:block">
                    <AppIcon
                        name="search"
                        class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3"
                    />
                    <input
                        type="search"
                        placeholder="Cari dataset atau analisis…"
                        class="focus-ring h-9 w-full rounded-lg border-hairline bg-plane pl-9 pr-3 text-sm text-ink placeholder:text-ink-3 focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                    />
                </div>

                <div class="ml-auto flex items-center gap-2">
                    <ThemeToggle />

                    <button
                        type="button"
                        class="focus-ring relative rounded-lg p-2 text-ink-2 hover:text-ink dark:text-ink-2-dark dark:hover:text-ink-dark"
                    >
                        <AppIcon name="bell" class="h-[18px] w-[18px]" />
                        <span
                            class="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-status-critical ring-2 ring-surface dark:ring-surface-dark"
                        />
                        <span class="sr-only">Notifikasi</span>
                    </button>

                    <RouterLink
                        :to="{ name: 'settings.index' }"
                        class="focus-ring rounded-lg p-2 text-ink-2 transition-colors hover:text-ink dark:text-ink-2-dark dark:hover:text-ink-dark"
                    >
                        <AppIcon name="settings" class="h-[18px] w-[18px]" />
                        <span class="sr-only">Pengaturan</span>
                    </RouterLink>
                </div>
            </header>

            <main class="px-4 py-6 sm:px-6 lg:px-8">
                <div class="mx-auto max-w-7xl">
                    <slot />
                </div>
            </main>
        </div>
    </div>
</template>
