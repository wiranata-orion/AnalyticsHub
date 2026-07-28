<script setup>
import { computed } from 'vue';
import { formatNumber } from '@/Utils/profiler';

/*
 * Boxplot sebagai elemen HTML, bukan chart canvas — sama seperti
 * CorrelationHeatmap. Chart.js tidak menyediakan controller boxplot, dan
 * bentuknya cukup sederhana untuk digambar dengan posisi persen. Keuntungannya
 * angka lima serangkai tetap bisa dipilih, dibaca screen reader, dan ikut Ctrl+F.
 *
 * Tiap baris dinormalisasi terhadap rentangnya sendiri karena kolom yang
 * ditampilkan bersatuan berbeda; nilainya selalu tercetak sebagai keterangan,
 * jadi panjang kotak tidak pernah jadi satu-satunya pembawa makna.
 */
const props = defineProps({
    // [{ label, min, q1, median, q3, max, lowerFence, upperFence, outlierCount }]
    boxes: {
        type: Array,
        required: true,
    },
});

const plots = computed(() =>
    props.boxes.map((box) => {
        const span = box.max - box.min || 1;
        const position = (value) => ((value - box.min) / span) * 100;

        return {
            box,
            // Persen posisi disimpan terpisah dari nilai aslinya supaya keduanya
            // tidak saling menimpa saat dirender.
            whiskerStart: position(box.lowerFence),
            whiskerEnd: position(box.upperFence),
            boxStart: position(box.q1),
            boxWidth: Math.max(position(box.q3) - position(box.q1), 0.8),
            medianAt: position(box.median),
            summary: [
                { label: 'min', value: box.min },
                { label: 'Q1', value: box.q1 },
                { label: 'median', value: box.median },
                { label: 'Q3', value: box.q3 },
                { label: 'maks', value: box.max },
            ],
        };
    }),
);
</script>

<template>
    <div class="space-y-5">
        <div v-for="plot in plots" :key="plot.box.label">
            <div class="mb-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <span class="truncate text-xs font-medium text-ink dark:text-ink-dark">
                    {{ plot.box.label }}
                </span>
                <span class="shrink-0 text-xs tabular-nums text-ink-3">
                    median {{ formatNumber(plot.box.median) }}
                    <template v-if="plot.box.outlierCount">
                        · {{ plot.box.outlierCount }} outlier
                    </template>
                </span>
            </div>

            <div class="relative h-7">
                <!-- Rentang wajar (dalam 1,5 × IQR) -->
                <div
                    class="absolute top-1/2 h-px -translate-y-1/2 bg-ink-3"
                    :style="{
                        left: `${plot.whiskerStart}%`,
                        width: `${plot.whiskerEnd - plot.whiskerStart}%`,
                    }"
                />
                <div
                    v-for="edge in [plot.whiskerStart, plot.whiskerEnd]"
                    :key="edge"
                    class="absolute top-1/2 h-3 w-px -translate-y-1/2 bg-ink-3"
                    :style="{ left: `${edge}%` }"
                />

                <!-- Kuartil 1 sampai kuartil 3 -->
                <div
                    class="absolute top-1/2 h-5 -translate-y-1/2 rounded-sm bg-accent/25 ring-1 ring-inset ring-accent dark:bg-accent-dark/25 dark:ring-accent-dark"
                    :style="{ left: `${plot.boxStart}%`, width: `${plot.boxWidth}%` }"
                />

                <!-- Median -->
                <div
                    class="absolute top-1/2 h-5 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-ink dark:bg-ink-dark"
                    :style="{ left: `${plot.medianAt}%` }"
                />
            </div>

            <dl
                class="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] tabular-nums text-ink-3"
            >
                <div
                    v-for="item in plot.summary"
                    :key="item.label"
                    class="flex gap-1"
                >
                    <dt>{{ item.label }}</dt>
                    <dd class="text-ink-2 dark:text-ink-2-dark">
                        {{ formatNumber(item.value) }}
                    </dd>
                </div>
            </dl>
        </div>
    </div>
</template>
