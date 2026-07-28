<script setup>
import { useToastStore } from '@/stores/toast';
import AppIcon from '@/Components/UI/AppIcon.vue';

/*
 * Penampil toast tunggal, dirender sekali di AppLayout.
 * Isi antreannya dikelola store `toast` — lihat komentar di sana.
 */
const toastStore = useToastStore();

const TONE_ICONS = {
    success: 'check',
    info: 'bell',
    warning: 'warning',
};

const TONE_CLASSES = {
    success: 'text-[#006300] dark:text-status-good',
    info: 'text-accent dark:text-accent-dark',
    warning: 'text-[#8a5a00] dark:text-status-warning',
};
</script>

<template>
    <div
        class="pointer-events-none fixed inset-x-0 bottom-4 z-[70] flex flex-col items-center gap-2 px-4 sm:items-end sm:px-6"
        aria-live="polite"
    >
        <TransitionGroup
            enter-active-class="transition ease-out duration-200"
            enter-from-class="translate-y-2 opacity-0"
            leave-active-class="transition ease-in duration-150"
            leave-to-class="opacity-0"
        >
            <div
                v-for="toast in toastStore.items"
                :key="toast.id"
                class="pointer-events-auto flex w-full max-w-sm items-start gap-2.5 rounded-xl border border-hairline bg-surface px-4 py-3 shadow-lg dark:border-hairline-dark dark:bg-raised-dark"
            >
                <AppIcon
                    :name="TONE_ICONS[toast.tone] ?? 'check'"
                    class="mt-0.5 h-4 w-4 shrink-0"
                    :class="TONE_CLASSES[toast.tone] ?? TONE_CLASSES.success"
                />
                <p class="min-w-0 flex-1 text-sm text-ink dark:text-ink-dark">
                    {{ toast.message }}
                </p>
                <button
                    type="button"
                    class="focus-ring -mr-1 rounded-md p-1 text-ink-3 hover:text-ink dark:hover:text-ink-dark"
                    @click="toastStore.dismiss(toast.id)"
                >
                    <AppIcon name="close" class="h-3.5 w-3.5" />
                    <span class="sr-only">Tutup notifikasi</span>
                </button>
            </div>
        </TransitionGroup>
    </div>
</template>
