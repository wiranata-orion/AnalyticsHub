<script setup>
import AppIcon from '@/Components/UI/AppIcon.vue';

defineProps({
    icon: {
        type: String,
        default: 'datasets',
    },
    title: {
        type: String,
        required: true,
    },
    description: {
        type: String,
        default: null,
    },
});
</script>

<template>
    <div class="flex flex-col items-center justify-center px-6 py-14 text-center">
        <div
            class="flex h-11 w-11 items-center justify-center rounded-full bg-plane text-ink-3 dark:bg-raised-dark"
        >
            <AppIcon :name="icon" class="h-5 w-5" />
        </div>

        <p class="mt-4 text-sm font-medium text-ink dark:text-ink-dark">
            {{ title }}
        </p>
        <p
            v-if="description"
            class="mt-1 max-w-sm text-sm text-ink-2 dark:text-ink-2-dark"
        >
            {{ description }}
        </p>

        <div v-if="$slots.action" class="mt-5">
            <slot name="action" />
        </div>
    </div>
</template>
