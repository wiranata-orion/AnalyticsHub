<script setup>
import { computed } from 'vue';
import AppIcon from '@/Components/UI/AppIcon.vue';

/*
 * Warna status tidak pernah berdiri sendiri: setiap varian bermakna membawa
 * ikon di samping teksnya, karena `warning` dan `serious` memang di bawah 3:1
 * pada permukaan terang.
 */
const props = defineProps({
    variant: {
        type: String,
        default: 'neutral',
        validator: (value) =>
            ['neutral', 'good', 'warning', 'serious', 'critical', 'info'].includes(
                value,
            ),
    },
});

const VARIANTS = {
    neutral: {
        classes:
            'bg-plane text-ink-2 ring-hairline dark:bg-raised-dark dark:text-ink-2-dark dark:ring-hairline-dark',
        icon: null,
    },
    info: {
        classes:
            'bg-[#cde2fb]/50 text-[#184f95] ring-[#9ec5f4] dark:bg-[#184f95]/25 dark:text-[#9ec5f4] dark:ring-[#256abf]',
        icon: null,
    },
    good: {
        classes:
            'bg-[#0ca30c]/10 text-[#006300] ring-[#0ca30c]/30 dark:text-status-good',
        icon: 'check',
    },
    warning: {
        classes:
            'bg-[#fab219]/15 text-[#8a5a00] ring-[#fab219]/40 dark:text-status-warning',
        icon: 'warning',
    },
    serious: {
        classes:
            'bg-[#ec835a]/15 text-[#a34418] ring-[#ec835a]/40 dark:text-status-serious',
        icon: 'warning',
    },
    critical: {
        classes:
            'bg-[#d03b3b]/10 text-[#a02020] ring-[#d03b3b]/30 dark:text-status-critical',
        icon: 'warning',
    },
};

const config = computed(() => VARIANTS[props.variant]);
</script>

<template>
    <span
        class="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset"
        :class="config.classes"
    >
        <AppIcon v-if="config.icon" :name="config.icon" class="h-3 w-3 shrink-0" />
        <slot />
    </span>
</template>
