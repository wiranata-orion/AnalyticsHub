<script setup>
import { computed } from 'vue';
import AppIcon from '@/Components/UI/AppIcon.vue';

/*
 * Angka tunggal yang berdiri sendiri — dipakai saat sebuah nilai tidak butuh
 * sumbu untuk dibaca. Delta selalu tampil sebagai ikon arah + tanda + label
 * periode, jadi maknanya tidak pernah bergantung pada warna saja.
 */
const props = defineProps({
    label: {
        type: String,
        required: true,
    },
    value: {
        type: [String, Number],
        required: true,
    },
    unit: {
        type: String,
        default: null,
    },
    icon: {
        type: String,
        default: null,
    },
    // Positif/negatif dalam persen. null = tidak ada pembanding.
    delta: {
        type: Number,
        default: null,
    },
    deltaLabel: {
        type: String,
        default: 'vs bulan lalu',
    },
    // Sebagian metrik membaik saat turun (mis. missing value).
    lowerIsBetter: {
        type: Boolean,
        default: false,
    },
});

const isImprovement = computed(() =>
    props.lowerIsBetter ? props.delta < 0 : props.delta > 0,
);

const deltaTone = computed(() =>
    isImprovement.value
        ? 'text-[#006300] dark:text-status-good'
        : 'text-status-critical',
);
</script>

<template>
    <div
        class="rounded-xl border border-hairline bg-surface p-5 dark:border-hairline-dark dark:bg-surface-dark"
    >
        <div class="flex items-center justify-between gap-3">
            <p
                class="truncate text-xs font-medium uppercase tracking-wide text-ink-3"
            >
                {{ label }}
            </p>
            <AppIcon v-if="icon" :name="icon" class="h-4 w-4 shrink-0 text-ink-3" />
        </div>

        <p class="mt-3 flex items-baseline gap-1.5">
            <span
                class="text-3xl font-semibold leading-none text-ink dark:text-ink-dark"
            >
                {{ value }}
            </span>
            <span v-if="unit" class="text-sm text-ink-2 dark:text-ink-2-dark">
                {{ unit }}
            </span>
        </p>

        <p
            v-if="delta !== null"
            class="mt-2.5 flex items-center gap-1 text-xs"
            :class="deltaTone"
        >
            <AppIcon
                :name="delta > 0 ? 'trendUp' : 'trendDown'"
                class="h-3.5 w-3.5 shrink-0"
            />
            <span class="font-medium">
                {{ delta > 0 ? '+' : '' }}{{ delta }}%
            </span>
            <span class="text-ink-3">{{ deltaLabel }}</span>
        </p>
    </div>
</template>
