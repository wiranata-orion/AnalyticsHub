<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { Chart } from '@/Utils/chartSetup';
import { useTheme } from '@/Composables/useTheme';
import { palette } from '@/Utils/palette';
import AppIcon from '@/Components/UI/AppIcon.vue';
import ChartLegend from '@/Components/Charts/ChartLegend.vue';

/*
 * Satu panel chart untuk seluruh aplikasi: kartu + legend + tooltip + table view.
 *
 * Chart.js dipakai langsung (bukan lewat pembungkus) karena satu komponen ini
 * melayani semua tipe chart, dan pergantian tema perlu mengecat ulang skala,
 * grid, serta warna seri sekaligus — lebih ringkas ditangani di satu tempat.
 *
 * Warna seri diambil BERURUTAN dari slot palet. Pemanggil tidak menentukan hex;
 * itu yang menjaga jaminan colorblind-safe tetap berlaku.
 */
const props = defineProps({
    title: {
        type: String,
        default: null,
    },
    subtitle: {
        type: String,
        default: null,
    },
    type: {
        type: String,
        default: 'line',
        validator: (value) =>
            ['line', 'area', 'bar', 'doughnut', 'scatter'].includes(value),
    },
    // Label sumbu X (tidak dipakai pada scatter).
    labels: {
        type: Array,
        default: () => [],
    },
    // [{ label, data }] — data berupa angka, atau {x, y} untuk scatter.
    series: {
        type: Array,
        required: true,
    },
    height: {
        type: Number,
        default: 260,
    },
    stacked: {
        type: Boolean,
        default: false,
    },
    horizontal: {
        type: Boolean,
        default: false,
    },
    valueSuffix: {
        type: String,
        default: '',
    },
});

const canvas = ref(null);
const showTable = ref(false);
let chart = null;

const { isDark } = useTheme();
const tokens = computed(() => palette(isDark.value));

const colors = computed(() =>
    props.series.map((_, index) => tokens.value.series[index % 8]),
);

const legendEntries = computed(() =>
    props.type === 'doughnut'
        ? props.labels.map((label, index) => ({
              label,
              color: tokens.value.series[index % 8],
              value: `${props.series[0].data[index]}${props.valueSuffix}`,
          }))
        : props.series.map((serie, index) => ({
              label: serie.label,
              color: colors.value[index],
          })),
);

// Seri tunggal tidak butuh kotak legend — judul panel sudah menamai datanya.
const showLegend = computed(
    () => props.type === 'doughnut' || props.series.length >= 2,
);

/*
 * Garis bidik vertikal untuk line/area. Chart.js tidak menyediakannya, dan
 * membaca nilai pada satu titik waktu tanpa garis ini jauh lebih sulit.
 */
const crosshairPlugin = {
    id: 'crosshair',
    afterDatasetsDraw(instance) {
        const active = instance.tooltip?.getActiveElements?.() ?? [];

        if (!active.length) {
            return;
        }

        const { ctx, chartArea } = instance;
        const x = active[0].element.x;

        ctx.save();
        ctx.beginPath();
        ctx.moveTo(x, chartArea.top);
        ctx.lineTo(x, chartArea.bottom);
        ctx.lineWidth = 1;
        ctx.strokeStyle = tokens.value.axis;
        ctx.stroke();
        ctx.restore();
    },
};

function buildDatasets() {
    const theme = tokens.value;

    if (props.type === 'doughnut') {
        return [
            {
                data: props.series[0].data,
                backgroundColor: props.labels.map(
                    (_, index) => theme.series[index % 8],
                ),
                // Cincin setebal 2px sewarna permukaan memisahkan segmen
                // bersebelahan tanpa menambah garis baru.
                borderColor: theme.surface,
                borderWidth: 2,
                hoverOffset: 4,
            },
        ];
    }

    return props.series.map((serie, index) => {
        const color = theme.series[index % 8];

        if (props.type === 'scatter') {
            return {
                label: serie.label,
                data: serie.data,
                backgroundColor: color,
                borderColor: theme.surface,
                borderWidth: 1.5,
                pointRadius: 4,
                pointHoverRadius: 6,
            };
        }

        if (props.type === 'bar') {
            return {
                label: serie.label,
                data: serie.data,
                backgroundColor: color,
                borderRadius: 4,
                borderSkipped: false,
                borderColor: theme.surface,
                borderWidth: { top: 0, right: 0, bottom: 0, left: 0 },
                categoryPercentage: 0.7,
                barPercentage: 0.9,
                maxBarThickness: 40,
            };
        }

        return {
            label: serie.label,
            data: serie.data,
            borderColor: color,
            backgroundColor:
                props.type === 'area' ? `${color}26` : 'transparent',
            fill: props.type === 'area',
            borderWidth: 2,
            tension: 0.35,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointBackgroundColor: color,
            pointBorderColor: theme.surface,
            pointBorderWidth: 2,
        };
    });
}

function buildOptions() {
    const theme = tokens.value;

    const tooltip = {
        backgroundColor: isDark.value ? '#242422' : '#0b0b0b',
        titleColor: '#ffffff',
        bodyColor: isDark.value ? '#c3c2b7' : '#e1e0d9',
        borderColor: isDark.value ? '#383835' : 'transparent',
        borderWidth: isDark.value ? 1 : 0,
        padding: 10,
        cornerRadius: 8,
        displayColors: true,
        boxWidth: 8,
        boxHeight: 8,
        boxPadding: 4,
        usePointStyle: true,
        callbacks: {
            label: (context) => {
                const value =
                    context.parsed.y ?? context.parsed.r ?? context.parsed;
                const shown = typeof value === 'object' ? value.y : value;

                return ` ${context.dataset.label ?? context.label}: ${shown}${props.valueSuffix}`;
            },
        },
    };

    if (props.type === 'doughnut') {
        return {
            responsive: true,
            cutout: '65%',
            plugins: {
                tooltip: {
                    ...tooltip,
                    callbacks: {
                        label: (context) =>
                            ` ${context.label}: ${context.parsed}${props.valueSuffix}`,
                    },
                },
            },
        };
    }

    const scale = {
        grid: {
            color: theme.grid,
            drawTicks: false,
        },
        border: { color: theme.axis },
        ticks: {
            color: theme.muted,
            font: { size: 11 },
            padding: 8,
        },
    };

    return {
        responsive: true,
        indexAxis: props.horizontal ? 'y' : 'x',
        interaction: {
            mode: props.type === 'scatter' ? 'nearest' : 'index',
            intersect: false,
        },
        plugins: { tooltip },
        scales: {
            x: {
                ...scale,
                stacked: props.stacked,
                grid: { ...scale.grid, display: props.horizontal },
            },
            y: {
                ...scale,
                stacked: props.stacked,
                beginAtZero: true,
                grid: { ...scale.grid, display: !props.horizontal },
            },
        },
    };
}

function render() {
    chart?.destroy();

    chart = new Chart(canvas.value, {
        type: props.type === 'area' ? 'line' : props.type,
        data: {
            labels: props.labels,
            datasets: buildDatasets(),
        },
        options: buildOptions(),
        plugins: ['line', 'area'].includes(props.type) ? [crosshairPlugin] : [],
    });
}

onMounted(render);
onBeforeUnmount(() => chart?.destroy());

// Tema mengubah warna grid, sumbu, dan seri sekaligus — bangun ulang instance
// lebih murah dan lebih aman daripada menambal setiap opsi satu per satu.
watch(isDark, render);
watch(() => [props.series, props.labels], render, { deep: true });
</script>

<template>
    <section
        class="rounded-xl border border-hairline bg-surface dark:border-hairline-dark dark:bg-surface-dark"
    >
        <header
            class="flex flex-wrap items-start justify-between gap-3 px-5 pb-3 pt-4"
        >
            <div class="min-w-0">
                <h3
                    v-if="title"
                    class="truncate text-sm font-semibold text-ink dark:text-ink-dark"
                >
                    {{ title }}
                </h3>
                <p v-if="subtitle" class="mt-0.5 text-xs text-ink-3">
                    {{ subtitle }}
                </p>
            </div>

            <div class="flex shrink-0 items-center gap-1">
                <slot name="actions" />

                <button
                    type="button"
                    class="focus-ring rounded-md p-1.5 transition-colors"
                    :class="
                        showTable
                            ? 'bg-plane text-ink dark:bg-raised-dark dark:text-ink-dark'
                            : 'text-ink-3 hover:text-ink dark:hover:text-ink-dark'
                    "
                    :aria-pressed="showTable"
                    :title="showTable ? 'Tampilkan grafik' : 'Tampilkan tabel'"
                    @click="showTable = !showTable"
                >
                    <AppIcon name="table" class="h-4 w-4" />
                    <span class="sr-only">Alihkan tampilan tabel</span>
                </button>
            </div>
        </header>

        <div v-show="!showTable" class="px-5">
            <div :style="{ height: `${height}px` }">
                <canvas ref="canvas" />
            </div>
        </div>

        <!-- Tampilan tabel: jalur baca alternatif saat warna tidak terbedakan. -->
        <div v-if="showTable" class="max-h-72 overflow-auto px-5">
            <table class="w-full text-sm">
                <thead
                    class="sticky top-0 bg-surface text-left dark:bg-surface-dark"
                >
                    <tr class="border-b border-hairline dark:border-hairline-dark">
                        <th
                            class="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-ink-3"
                        >
                            {{ type === 'scatter' ? 'Seri' : 'Label' }}
                        </th>
                        <th
                            v-for="(column, index) in type === 'doughnut'
                                ? ['Nilai']
                                : series.map((s) => s.label)"
                            :key="index"
                            class="py-2 pl-4 text-right text-xs font-medium uppercase tracking-wide text-ink-3"
                        >
                            {{ column }}
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="(label, rowIndex) in labels"
                        :key="label"
                        class="border-b border-hairline last:border-0 dark:border-hairline-dark"
                    >
                        <td class="py-2 pr-4 text-ink-2 dark:text-ink-2-dark">
                            {{ label }}
                        </td>
                        <td
                            v-for="(serie, colIndex) in series"
                            :key="colIndex"
                            class="py-2 pl-4 text-right tabular-nums text-ink dark:text-ink-dark"
                        >
                            {{ serie.data[rowIndex] }}{{ valueSuffix }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <footer
            v-if="showLegend"
            class="border-t border-hairline px-5 py-3 dark:border-hairline-dark"
        >
            <ChartLegend :entries="legendEntries" />
        </footer>
        <div v-else class="pb-4" />
    </section>
</template>
