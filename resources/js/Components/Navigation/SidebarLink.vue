<script setup>
import { RouterLink } from 'vue-router';
import AppIcon from '@/Components/UI/AppIcon.vue';

/*
 * Status aktif tidak dibawa warna saja: item aktif mendapat pita di tepi kiri,
 * latar terangkat, dan bobot huruf lebih tebal.
 */
defineProps({
    to: {
        type: [String, Object],
        required: true,
    },
    icon: {
        type: String,
        required: true,
    },
    active: {
        type: Boolean,
        default: false,
    },
    badge: {
        type: [String, Number],
        default: null,
    },
});
</script>

<template>
    <RouterLink
        :to="to"
        class="focus-ring group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors"
        :class="
            active
                ? 'bg-plane font-medium text-ink dark:bg-raised-dark dark:text-ink-dark'
                : 'text-ink-2 hover:bg-plane hover:text-ink dark:text-ink-2-dark dark:hover:bg-raised-dark dark:hover:text-ink-dark'
        "
        :aria-current="active ? 'page' : undefined"
    >
        <span
            v-if="active"
            class="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-accent dark:bg-accent-dark"
            aria-hidden="true"
        />

        <AppIcon
            :name="icon"
            class="h-[18px] w-[18px] shrink-0"
            :class="active ? 'text-accent dark:text-accent-dark' : 'text-ink-3'"
        />

        <span class="truncate"><slot /></span>

        <span
            v-if="badge"
            class="ml-auto shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-ink-3 ring-1 ring-inset ring-hairline dark:ring-hairline-dark"
        >
            {{ badge }}
        </span>
    </RouterLink>
</template>
