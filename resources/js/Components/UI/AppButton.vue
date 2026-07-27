<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import AppIcon from '@/Components/UI/AppIcon.vue';

const props = defineProps({
    variant: {
        type: String,
        default: 'secondary',
        validator: (value) =>
            ['primary', 'secondary', 'ghost', 'danger'].includes(value),
    },
    size: {
        type: String,
        default: 'md',
        validator: (value) => ['sm', 'md'].includes(value),
    },
    icon: {
        type: String,
        default: null,
    },
    // Saat diisi, dirender sebagai <RouterLink> alih-alih <button>.
    to: {
        type: [String, Object],
        default: null,
    },
    disabled: {
        type: Boolean,
        default: false,
    },
});

const VARIANTS = {
    primary:
        'bg-accent text-white hover:bg-[#256abf] dark:bg-accent-dark dark:hover:bg-[#2a78d6]',
    secondary:
        'bg-surface text-ink ring-1 ring-inset ring-hairline hover:bg-plane dark:bg-raised-dark dark:text-ink-dark dark:ring-hairline-dark dark:hover:bg-[#2c2c2a]',
    ghost: 'text-ink-2 hover:bg-plane hover:text-ink dark:text-ink-2-dark dark:hover:bg-raised-dark dark:hover:text-ink-dark',
    danger: 'bg-status-critical text-white hover:bg-[#a02020]',
};

const SIZES = {
    sm: 'h-8 px-2.5 text-xs gap-1.5',
    md: 'h-9 px-3.5 text-sm gap-2',
};

const classes = computed(() => [
    'focus-ring inline-flex items-center justify-center rounded-lg font-medium transition-colors',
    VARIANTS[props.variant],
    SIZES[props.size],
    props.disabled ? 'pointer-events-none opacity-50' : '',
]);

const iconSize = computed(() => (props.size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'));
</script>

<template>
    <RouterLink v-if="to" :to="to" :class="classes">
        <AppIcon v-if="icon" :name="icon" :class="[iconSize, 'shrink-0']" />
        <slot />
    </RouterLink>

    <button v-else type="button" :class="classes" :disabled="disabled">
        <AppIcon v-if="icon" :name="icon" :class="[iconSize, 'shrink-0']" />
        <slot />
    </button>
</template>
