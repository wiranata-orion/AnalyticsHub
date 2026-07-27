<script setup>
defineProps({
    title: {
        type: String,
        default: null,
    },
    subtitle: {
        type: String,
        default: null,
    },
    // Konten padat seperti tabel mengatur paddingnya sendiri per sel.
    flush: {
        type: Boolean,
        default: false,
    },
});
</script>

<template>
    <section
        class="rounded-xl border border-hairline bg-surface dark:border-hairline-dark dark:bg-surface-dark"
    >
        <header
            v-if="title || subtitle || $slots.actions"
            class="flex items-start justify-between gap-4 border-b border-hairline px-5 py-4 dark:border-hairline-dark"
        >
            <div class="min-w-0">
                <h3
                    v-if="title"
                    class="truncate text-sm font-semibold text-ink dark:text-ink-dark"
                >
                    {{ title }}
                </h3>
                <p
                    v-if="subtitle"
                    class="mt-0.5 text-xs text-ink-2 dark:text-ink-2-dark"
                >
                    {{ subtitle }}
                </p>
            </div>

            <div v-if="$slots.actions" class="shrink-0">
                <slot name="actions" />
            </div>
        </header>

        <div :class="flush ? '' : 'p-5'">
            <slot />
        </div>

        <footer
            v-if="$slots.footer"
            class="border-t border-hairline px-5 py-3 dark:border-hairline-dark"
        >
            <slot name="footer" />
        </footer>
    </section>
</template>
