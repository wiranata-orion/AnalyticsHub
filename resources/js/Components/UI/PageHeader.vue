<script setup>
import { RouterLink } from 'vue-router';
import AppIcon from '@/Components/UI/AppIcon.vue';

defineProps({
    title: {
        type: String,
        required: true,
    },
    description: {
        type: String,
        default: null,
    },
    // Daftar { label, to? }. Item terakhir dirender sebagai teks biasa.
    breadcrumbs: {
        type: Array,
        default: () => [],
    },
});
</script>

<template>
    <header class="mb-6">
        <nav
            v-if="breadcrumbs.length"
            aria-label="Breadcrumb"
            class="mb-2 flex items-center gap-1 text-xs text-ink-3"
        >
            <template v-for="(crumb, index) in breadcrumbs" :key="crumb.label">
                <AppIcon
                    v-if="index > 0"
                    name="chevronRight"
                    class="h-3 w-3 shrink-0"
                />
                <RouterLink
                    v-if="crumb.to"
                    :to="crumb.to"
                    class="focus-ring rounded transition-colors hover:text-ink dark:hover:text-ink-dark"
                >
                    {{ crumb.label }}
                </RouterLink>
                <span v-else class="text-ink-2 dark:text-ink-2-dark">
                    {{ crumb.label }}
                </span>
            </template>
        </nav>

        <div class="flex flex-wrap items-end justify-between gap-4">
            <div class="min-w-0">
                <h1
                    class="text-2xl font-semibold tracking-tight text-ink dark:text-ink-dark"
                >
                    {{ title }}
                </h1>
                <p
                    v-if="description"
                    class="mt-1 max-w-2xl text-sm text-ink-2 dark:text-ink-2-dark"
                >
                    {{ description }}
                </p>
            </div>

            <div v-if="$slots.actions" class="flex shrink-0 items-center gap-2">
                <slot name="actions" />
            </div>
        </div>
    </header>
</template>
