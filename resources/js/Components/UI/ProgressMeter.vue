<script setup>
import { computed } from 'vue';

/*
 * Bar proporsi satu nilai. Angka persennya selalu tercetak di samping bar —
 * beberapa langkah warna seri berada di bawah 3:1 pada permukaan terang,
 * sehingga panjang bar saja tidak boleh menjadi satu-satunya pembawa makna.
 */
const props = defineProps({
    label: {
        type: String,
        required: true,
    },
    value: {
        type: Number,
        required: true,
    },
    max: {
        type: Number,
        default: 100,
    },
    // Hex eksplisit dari palet seri; default memakai slot 1.
    color: {
        type: String,
        default: null,
    },
    caption: {
        type: String,
        default: null,
    },
});

const percent = computed(() =>
    Math.min(100, Math.round((props.value / props.max) * 1000) / 10),
);
</script>

<template>
    <div>
        <div class="mb-1.5 flex items-baseline justify-between gap-3">
            <span class="truncate text-xs text-ink-2 dark:text-ink-2-dark">
                {{ label }}
            </span>
            <span
                class="shrink-0 text-xs font-medium tabular-nums text-ink dark:text-ink-dark"
            >
                {{ caption ?? `${percent}%` }}
            </span>
        </div>

        <div
            class="h-1.5 w-full overflow-hidden rounded-full bg-plane dark:bg-raised-dark"
            role="progressbar"
            :aria-valuenow="percent"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="label"
        >
            <div
                class="h-full rounded-full transition-[width] duration-500"
                :style="{
                    width: `${percent}%`,
                    backgroundColor: color ?? 'currentColor',
                }"
                :class="color ? '' : 'text-accent dark:text-accent-dark'"
            />
        </div>
    </div>
</template>
