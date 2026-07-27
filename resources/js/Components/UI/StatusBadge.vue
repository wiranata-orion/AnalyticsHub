<script setup>
import { computed } from 'vue';
import AppBadge from '@/Components/UI/AppBadge.vue';

/*
 * Pemetaan tunggal status -> label + varian, supaya istilah yang sama tidak
 * diterjemahkan berbeda di tiap tabel.
 */
const props = defineProps({
    status: {
        type: String,
        required: true,
    },
});

const MAP = {
    ready: { label: 'Siap', variant: 'good' },
    processing: { label: 'Diproses', variant: 'info' },
    training: { label: 'Melatih', variant: 'info' },
    generating: { label: 'Membuat', variant: 'info' },
    queued: { label: 'Antre', variant: 'neutral' },
    failed: { label: 'Gagal', variant: 'critical' },
};

const config = computed(
    () => MAP[props.status] ?? { label: props.status, variant: 'neutral' },
);
</script>

<template>
    <AppBadge :variant="config.variant">{{ config.label }}</AppBadge>
</template>
