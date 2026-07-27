import { computed, onMounted, onUnmounted, ref } from 'vue';

const STORAGE_KEY = 'analyticshub.theme';

/*
 * State modul, bukan state komponen: seluruh aplikasi harus melihat satu tema
 * yang sama. Jika ini di-`ref` di dalam fungsi, tiap pemanggil useTheme() akan
 * punya salinan sendiri dan toggle di topbar tidak akan mengecat ulang chart.
 */
const preference = ref('system');
const systemPrefersDark = ref(false);

function readStoredPreference() {
    try {
        return localStorage.getItem(STORAGE_KEY) || 'system';
    } catch (e) {
        return 'system';
    }
}

function persistPreference(value) {
    try {
        localStorage.setItem(STORAGE_KEY, value);
    } catch (e) {
        // Penyimpanan tidak tersedia — tema tetap berlaku untuk sesi ini.
    }
}

const isDark = computed(
    () =>
        preference.value === 'dark' ||
        (preference.value === 'system' && systemPrefersDark.value),
);

function applyToDocument() {
    const root = document.documentElement;

    root.classList.toggle('dark', isDark.value);
    root.dataset.theme = isDark.value ? 'dark' : 'light';
}

export function useTheme() {
    let media = null;

    const handleSystemChange = (event) => {
        systemPrefersDark.value = event.matches;
        applyToDocument();
    };

    onMounted(() => {
        media = window.matchMedia('(prefers-color-scheme: dark)');
        systemPrefersDark.value = media.matches;
        preference.value = readStoredPreference();

        applyToDocument();
        media.addEventListener('change', handleSystemChange);
    });

    onUnmounted(() => media?.removeEventListener('change', handleSystemChange));

    function setTheme(value) {
        preference.value = value;
        persistPreference(value);
        applyToDocument();
    }

    /** Siklus terang -> gelap -> ikut sistem. */
    function cycleTheme() {
        const order = ['light', 'dark', 'system'];
        const next = order[(order.indexOf(preference.value) + 1) % order.length];

        setTheme(next);
    }

    return { preference, isDark, setTheme, cycleTheme };
}
