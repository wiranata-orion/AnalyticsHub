<script setup>
import { useTheme } from '@/Composables/useTheme';
import AppIcon from '@/Components/UI/AppIcon.vue';

/*
 * Kontrol tiga status, bukan sakelar dua status: "ikut sistem" adalah pilihan
 * tersendiri dan harus bisa dipilih kembali setelah pengguna memaksa salah satu.
 */
const { preference, setTheme } = useTheme();

const OPTIONS = [
    { value: 'light', icon: 'sun', label: 'Tema terang' },
    { value: 'dark', icon: 'moon', label: 'Tema gelap' },
    { value: 'system', icon: 'system', label: 'Ikut sistem' },
];
</script>

<template>
    <div
        class="flex items-center gap-0.5 rounded-lg border border-hairline bg-surface p-0.5 dark:border-hairline-dark dark:bg-surface-dark"
        role="group"
        aria-label="Pilihan tema"
    >
        <button
            v-for="option in OPTIONS"
            :key="option.value"
            type="button"
            class="focus-ring flex h-7 w-7 items-center justify-center rounded-md transition-colors"
            :class="
                preference === option.value
                    ? 'bg-plane text-ink dark:bg-raised-dark dark:text-ink-dark'
                    : 'text-ink-3 hover:text-ink dark:hover:text-ink-dark'
            "
            :aria-pressed="preference === option.value"
            :title="option.label"
            @click="setTheme(option.value)"
        >
            <AppIcon :name="option.icon" class="h-4 w-4" />
            <span class="sr-only">{{ option.label }}</span>
        </button>
    </div>
</template>
