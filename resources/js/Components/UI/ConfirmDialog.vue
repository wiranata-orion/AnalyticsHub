<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { useConfirmStore } from '@/stores/confirm';
import AppButton from '@/Components/UI/AppButton.vue';

/*
 * Penampil dialog konfirmasi tunggal, dirender sekali di AppLayout.
 * Pembukaannya dikelola store `confirm` — lihat komentar di sana.
 */
const confirmStore = useConfirmStore();
const panel = ref(null);

function onKeydown(event) {
    if (event.key === 'Escape') {
        confirmStore.close(false);
    }
}

// Fokus diarahkan ke tombol batal (aksi teraman) setiap dialog terbuka.
watch(
    () => confirmStore.isOpen,
    async (open) => {
        if (open) {
            window.addEventListener('keydown', onKeydown);
            await nextTick();
            panel.value?.querySelector('button')?.focus();
        } else {
            window.removeEventListener('keydown', onKeydown);
        }
    },
);

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown));
</script>

<template>
    <Transition
        enter-active-class="transition-opacity ease-out duration-150"
        enter-from-class="opacity-0"
        leave-active-class="transition-opacity ease-in duration-100"
        leave-to-class="opacity-0"
    >
        <div
            v-if="confirmStore.isOpen"
            class="fixed inset-0 z-[80] flex items-center justify-center p-4"
        >
            <div
                class="absolute inset-0 bg-ink/40"
                @click="confirmStore.close(false)"
            />

            <div
                ref="panel"
                role="dialog"
                aria-modal="true"
                :aria-label="confirmStore.options.title"
                class="relative w-full max-w-sm rounded-xl border border-hairline bg-surface p-5 shadow-xl dark:border-hairline-dark dark:bg-surface-dark"
            >
                <h2 class="text-sm font-semibold text-ink dark:text-ink-dark">
                    {{ confirmStore.options.title }}
                </h2>
                <p class="mt-2 text-sm text-ink-2 dark:text-ink-2-dark">
                    {{ confirmStore.options.message }}
                </p>

                <div class="mt-5 flex justify-end gap-2">
                    <AppButton @click="confirmStore.close(false)">Batal</AppButton>
                    <AppButton
                        :variant="confirmStore.options.tone"
                        @click="confirmStore.close(true)"
                    >
                        {{ confirmStore.options.confirmLabel }}
                    </AppButton>
                </div>
            </div>
        </div>
    </Transition>
</template>
