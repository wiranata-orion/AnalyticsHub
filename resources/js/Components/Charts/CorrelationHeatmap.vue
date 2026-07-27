<script setup>
import { computed } from 'vue';
import { useTheme } from '@/Composables/useTheme';
import { divergingAt, divergingInk } from '@/Utils/palette';

/*
 * Matriks korelasi sebagai grid HTML, bukan chart canvas.
 *
 * Matriksnya kecil dan tiap sel perlu memuat angkanya sendiri — HTML membuat
 * angka itu bisa dipilih, terbaca screen reader, dan ikut Ctrl+F. Koefisien
 * selalu tercetak, sehingga warna hanya mempercepat pemindaian, bukan syarat
 * untuk membacanya.
 */
const props = defineProps({
    // Nama kolom, urut sesuai baris/kolom matriks.
    columns: {
        type: Array,
        required: true,
    },
    // Matriks persegi nilai -1..1.
    matrix: {
        type: Array,
        required: true,
    },
});

const { isDark } = useTheme();

const cells = computed(() =>
    props.matrix.map((row) =>
        row.map((value) => ({
            value,
            background: divergingAt(value, isDark.value),
            color: divergingInk(value, isDark.value),
        })),
    ),
);

// Skala dibaca dari -1 ke 1 dengan abu netral di tengah.
const scaleStops = computed(() =>
    [-1, -0.5, 0, 0.5, 1].map((stop) => ({
        stop,
        background: divergingAt(stop, isDark.value),
    })),
);
</script>

<template>
    <div>
        <div class="overflow-x-auto">
            <table class="border-separate border-spacing-0.5 text-xs">
                <thead>
                    <tr>
                        <th class="sticky left-0 bg-surface dark:bg-surface-dark" />
                        <th
                            v-for="column in columns"
                            :key="column"
                            scope="col"
                            class="px-1 pb-1.5 text-center font-medium text-ink-3"
                        >
                            {{ column }}
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(row, rowIndex) in cells" :key="columns[rowIndex]">
                        <th
                            scope="row"
                            class="sticky left-0 whitespace-nowrap bg-surface pr-2.5 text-right font-medium text-ink-2 dark:bg-surface-dark dark:text-ink-2-dark"
                        >
                            {{ columns[rowIndex] }}
                        </th>
                        <td
                            v-for="(cell, colIndex) in row"
                            :key="colIndex"
                            class="h-9 min-w-[3.25rem] rounded text-center tabular-nums"
                            :style="{
                                backgroundColor: cell.background,
                                color: cell.color,
                            }"
                            :title="`${columns[rowIndex]} ↔ ${columns[colIndex]}: ${cell.value.toFixed(2)}`"
                        >
                            {{ cell.value.toFixed(2) }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="mt-4 flex items-center gap-2">
            <span class="text-xs text-ink-3">−1</span>
            <div class="flex h-2 flex-1 overflow-hidden rounded-full">
                <span
                    v-for="item in scaleStops"
                    :key="item.stop"
                    class="h-full flex-1"
                    :style="{ backgroundColor: item.background }"
                />
            </div>
            <span class="text-xs text-ink-3">+1</span>
            <span class="ml-1 text-xs text-ink-2 dark:text-ink-2-dark">
                merah = negatif · abu = tidak berkorelasi · biru = positif
            </span>
        </div>
    </div>
</template>
