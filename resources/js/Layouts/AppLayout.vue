<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import AppIcon from '@/Components/UI/AppIcon.vue';
import SidebarLink from '@/Components/Navigation/SidebarLink.vue';
import ThemeToggle from '@/Components/UI/ThemeToggle.vue';
import ToastHost from '@/Components/UI/ToastHost.vue';
import ConfirmDialog from '@/Components/UI/ConfirmDialog.vue';
import { useToastStore } from '@/stores/toast';
import { useDatasetStore } from '@/stores/dataset';

/*
 * Shell aplikasi: sidebar tetap di layar besar, drawer di layar kecil.
 *
 * Navigasi didefinisikan sebagai data, bukan markup berulang — menambah menu
 * cukup menambah satu entri. `match` adalah awalan nama rute, sehingga
 * `/datasets/create` tetap menyalakan menu "Dataset".
 */
const route = useRoute();
const sidebarOpen = ref(false);
const toast = useToastStore();
const datasetStore = useDatasetStore();

// Daftar dataset dimuat sekali di shell, bukan di tiap halaman: semua halaman
// analisis membutuhkannya, dan pilihan pengguna bertahan lintas menu.
onMounted(() => {
    if (!datasetStore.items.length && !datasetStore.isLoading) {
        datasetStore.fetchAll();
    }
});

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
            { label: 'EDA', icon: 'eda', name: 'eda.index', match: 'eda' },
            { label: 'Analisis Statistik', icon: 'statistical-analysis', name: 'statistical-analysis.index', match: 'statistical-analysis' },
            { label: 'Data Quality', icon: 'data-quality', name: 'data-quality.index', match: 'data-quality' },
        ],
    },

    {
        label: 'AI & Mining',
        items: [
            { label: 'Auto Recommendation', icon: 'auto-recommendation', name: 'auto-recommendation.index', match: 'auto-recommendation' },
            { label: 'Data Mining', icon: 'mining', name: 'mining.index', match: 'mining' },
            { label: 'Feature Engineering', icon: 'feature-engineering', name: 'feature-engineering.index', match: 'feature-engineering' },
            { label: 'Machine Learning', icon: 'ml', name: 'machine-learning.index', match: 'machine-learning' },
            { label: 'AutoML', icon: 'automl', name: 'automl.index', match: 'automl' },
            { label: 'Model Comparison', icon: 'model-comparison', name: 'model-comparison.index', match: 'model-comparison' },
            { label: 'Explainable AI', icon: 'explainable-ai', name: 'explainable-ai.index', match: 'explainable-ai' },
            { label: 'Forecasting', icon: 'forecasting', name: 'forecasting.index', match: 'forecasting' },
        ],
    },

    {
        label: 'Keluaran',
        items: [
            { label: 'Laporan', icon: 'reports', name: 'reports.index', match: 'reports' },
            { label: 'Auto Insight', icon: 'auto-insight', name: 'auto-insight.index', match: 'auto-insight' },
        ],
    },
];
const currentName = computed(() => String(route.name ?? ''));

const isActive = (match) =>
    currentName.value === match || currentName.value.startsWith(`${match}.`);

/*
 * Lebar sidebar pada layar besar: penuh -> ikon saja -> tersembunyi -> ikon saja
 * -> penuh, dan seterusnya.
 *
 * Siklusnya memantul, bukan berputar: dari keadaan tersembunyi, tekanan
 * berikutnya kembali ke ikon saja — bukan langsung melompat ke penuh. Itu
 * membuat satu tekanan selalu berarti satu langkah kecil, sehingga pengguna
 * dapat berhenti di lebar mana pun tanpa harus memutari seluruh siklus.
 */
const MODES = ['full', 'icons', 'hidden'];
const modeIndex = ref(0);
const direction = ref(1);

const sidebarMode = computed(() => MODES[modeIndex.value]);
const isCollapsed = computed(() => sidebarMode.value === 'icons');

/*
 * Lebar dipakai dua tempat (sidebar dan padding konten) dan wajib sama persis;
 * disimpan sekali agar keduanya tidak bisa saling menyimpang.
 *
 * Ditulis sebagai gaya sebaris, bukan kelas Tailwind: menganimasikan pergantian
 * kelas membuat peramban menghitung ulang lebar dari nol setiap langkah dan
 * hasilnya tersendat. Nilai piksel eksplisit membuat transisinya mulus.
 */
const SIDEBAR_WIDTH = { full: '16rem', icons: '4rem', hidden: '0rem' };

function cycleSidebar() {
    const next = modeIndex.value + direction.value;

    // Pada ujung siklus, arah dibalik lebih dulu supaya tekanan ini tetap
    // menghasilkan perpindahan satu langkah.
    if (next < 0 || next >= MODES.length) {
        direction.value *= -1;
        modeIndex.value += direction.value;

        return;
    }

    modeIndex.value = next;
}

const cycleLabel = computed(
    () =>
        ({
            full: 'Sembunyikan nama menu',
            icons: direction.value > 0 ? 'Sembunyikan sidebar' : 'Tampilkan nama menu',
            hidden: 'Tampilkan ikon menu',
        })[sidebarMode.value],
);

/*
 * Lebar hanya berlaku di layar besar. Di layar kecil sidebar adalah drawer
 * selebar penuh yang digeser masuk-keluar, jadi gaya sebarisnya dinetralkan.
 */
const isDesktopViewport = ref(
    typeof window !== 'undefined' && window.matchMedia('(min-width: 1024px)').matches,
);

const sidebarStyle = computed(() =>
    isDesktopViewport.value ? { width: SIDEBAR_WIDTH[sidebarMode.value] } : {},
);

const contentStyle = computed(() =>
    isDesktopViewport.value ? { paddingLeft: SIDEBAR_WIDTH[sidebarMode.value] } : {},
);

const isDesktop = () => isDesktopViewport.value;

onMounted(() => {
    const query = window.matchMedia('(min-width: 1024px)');
    const sync = (event) => (isDesktopViewport.value = event.matches);

    query.addEventListener('change', sync);
    onBeforeUnmount(() => query.removeEventListener('change', sync));
});

/*
 * Tombol yang sama melayani dua kebutuhan berbeda: di layar kecil sidebar berupa
 * drawer yang menutupi konten, jadi yang masuk akal hanyalah membuka/menutupnya.
 * Siklus lebar hanya berarti di layar besar tempat sidebar berbagi ruang dengan
 * konten.
 */
function handleMenuClick() {
    if (isDesktop()) {
        cycleSidebar();

        return;
    }

    sidebarOpen.value = !sidebarOpen.value;
}

const menuLabel = computed(() =>
    typeof window !== 'undefined' && isDesktop()
        ? cycleLabel.value
        : sidebarOpen.value
          ? 'Tutup navigasi'
          : 'Buka navigasi',
);

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
            class="fixed inset-y-0 left-0 z-50 flex w-64 flex-col overflow-hidden border-r border-hairline bg-surface transition-[width,transform] duration-300 ease-in-out dark:border-hairline-dark dark:bg-surface-dark lg:translate-x-0"
            :class="[
                sidebarOpen ? 'translate-x-0' : '-translate-x-full',
                sidebarMode === 'hidden' ? 'lg:border-r-0' : '',
            ]"
            :style="sidebarStyle"
        >
            <div
                class="flex h-14 shrink-0 items-center gap-2 border-b border-hairline px-3 dark:border-hairline-dark"
                :class="isCollapsed ? 'lg:justify-center' : 'justify-between'"
            >
                <!-- Tombol siklus ada DI DALAM sidebar, menempel pada elemen yang
                     diaturnya. Di layar kecil ia menutup drawer. -->
                <button
                    type="button"
                    class="focus-ring shrink-0 rounded-lg p-1.5 text-ink-2 transition-colors hover:bg-plane hover:text-ink dark:text-ink-2-dark dark:hover:bg-raised-dark dark:hover:text-ink-dark"
                    :title="menuLabel"
                    @click="handleMenuClick"
                >
                    <AppIcon name="menu" class="h-5 w-5" />
                    <span class="sr-only">{{ menuLabel }}</span>
                </button>

                <span
                    class="min-w-0 flex-1 truncate whitespace-nowrap text-sm font-semibold tracking-tight text-ink transition-opacity duration-200 dark:text-ink-dark"
                    :class="isCollapsed ? 'lg:pointer-events-none lg:absolute lg:opacity-0' : 'opacity-100'"
                >
                    AnalyticsHub
                </span>
            </div>

            <nav
                class="flex-1 space-y-5 overflow-y-auto py-4"
                :class="isCollapsed ? 'px-2' : 'px-3'"
            >
                <div v-for="(group, index) in NAV_GROUPS" :key="index">
                    <!-- Judul grup diganti garis pemisah saat menyempit: teks
                         sependek apa pun tidak muat di lebar ikon. -->
                    <p
                        v-if="group.label && !isCollapsed"
                        class="mb-1.5 px-3 text-[11px] font-medium uppercase tracking-wider text-ink-3"
                    >
                        {{ group.label }}
                    </p>
                    <hr
                        v-else-if="group.label"
                        class="mx-2 mb-1.5 border-hairline dark:border-hairline-dark"
                    />

                    <div class="space-y-0.5">
                        <SidebarLink
                            v-for="item in group.items"
                            :key="item.name"
                            :to="{ name: item.name }"
                            :icon="item.icon"
                            :active="isActive(item.match)"
                            :collapsed="isCollapsed"
                            :label="item.label"
                        >
                            {{ item.label }}
                        </SidebarLink>
                    </div>
                </div>
            </nav>
        </aside>

        <!-- Area konten -->
        <div
            class="transition-[padding] duration-300 ease-in-out"
            :style="contentStyle"
        >
            <header
                class="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-hairline bg-surface/85 px-4 backdrop-blur dark:border-hairline-dark dark:bg-surface-dark/85 sm:px-6"
            >
                <!-- Saat sidebar tersembunyi seluruhnya, tidak ada lagi tombol di
                     dalamnya — jadi satu-satunya jalan kembali disediakan di sini.
                     Di layar kecil tombol ini yang membuka drawer. -->
                <button
                    type="button"
                    class="focus-ring -ml-1 rounded-lg p-1.5 text-ink-2 transition-colors hover:text-ink dark:text-ink-2-dark dark:hover:text-ink-dark"
                    :class="sidebarMode === 'hidden' ? '' : 'lg:hidden'"
                    :title="menuLabel"
                    @click="handleMenuClick"
                >
                    <AppIcon name="menu" class="h-5 w-5" />
                    <span class="sr-only">{{ menuLabel }}</span>
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
                        @click="toast.push('Belum ada notifikasi baru.', 'info')"
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

        <ToastHost />
        <ConfirmDialog />
    </div>
</template>
