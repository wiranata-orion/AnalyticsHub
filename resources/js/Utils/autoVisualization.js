/*
 * Auto Visualization: menyusun konfigurasi grafik dari hasil profiling.
 *
 * Padanan modul `python/visualization/*`. Aturannya mengikuti tipe kolom, bukan
 * pilihan pengguna — begitu profiling selesai, halaman Visualisasi langsung
 * terisi tanpa konfigurasi apa pun:
 *
 *   numerik    -> histogram, boxplot, scatter pasangan terkuat, heatmap korelasi
 *   kategorikal-> bar chart, pie chart
 *   datetime   -> line chart, trend chart (rata-rata bergerak)
 *
 * Yang dikembalikan adalah KONFIGURASI, bukan grafik jadi. Bentuknya sama persis
 * dengan yang dihasilkan formulir pengguna, sehingga setiap panel otomatis bisa
 * langsung dibuka dan diubah — tidak perlu daftar grafik terpisah.
 *
 * Jumlah panel dibatasi supaya halaman tetap bisa dipindai: dataset dengan 30
 * kolom numerik tidak boleh menghasilkan 30 histogram.
 */

import { suggestGrain } from '@/Utils/chartBuilder';
import { strongestPair } from '@/Utils/profiler';

const MAX_HISTOGRAM = 3;
const MAX_CATEGORY_CHARTS = 2;
const BOXPLOT_COLUMNS = 4;
const PIE_MAX_CLASSES = 6;
const BAR_MAX_CLASSES = 12;

/** Nilai bawaan sebuah konfigurasi; medan yang tidak dipakai tetap ada agar
 *  formulir tidak perlu menangani properti yang hilang. */
export function emptyConfig(overrides = {}) {
    return {
        title: '',
        type: 'bar',
        xColumn: '',
        yColumn: '',
        aggregation: 'count',
        colorColumn: '',
        filterColumn: '',
        filterValue: '',
        timeGrain: 'day',
        smooth: false,
        columns: [],
        ...overrides,
    };
}

function timeConfigs(profile, table) {
    const timeColumn = profile.datetime[0];
    const valueColumn = profile.numeric[0];

    if (!timeColumn || !valueColumn) {
        return [];
    }

    const timeGrain = suggestGrain(
        table.rows.map((row) => row[timeColumn.name]),
    );

    const base = {
        xColumn: timeColumn.name,
        yColumn: valueColumn.name,
        aggregation: 'avg',
        timeGrain,
    };

    return [
        emptyConfig({ ...base, type: 'line' }),
        emptyConfig({
            ...base,
            type: 'area',
            smooth: true,
            title: `Tren ${valueColumn.name}`,
        }),
    ];
}

function histogramConfigs(profile) {
    // Kolom dengan sebaran paling lebar lebih informatif untuk ditampilkan lebih
    // dulu daripada kolom yang nilainya nyaris seragam.
    return [...profile.numeric]
        .sort((a, b) => {
            const spread = (column) =>
                column.mean ? Math.abs(column.std / column.mean) : 0;

            return spread(b) - spread(a);
        })
        .slice(0, MAX_HISTOGRAM)
        .map((column) =>
            emptyConfig({
                type: 'bar',
                xColumn: column.name,
                aggregation: 'count',
                title: `Sebaran ${column.name}`,
            }),
        );
}

function categoryConfigs(profile) {
    return profile.categorical
        .filter((column) => column.unique <= BAR_MAX_CLASSES)
        .slice(0, MAX_CATEGORY_CHARTS)
        .map((column, index) =>
            emptyConfig({
                // Pie hanya untuk kategori sedikit — di atas itu irisan kecil
                // tidak terbaca dan bar chart lebih tepat.
                type:
                    index === 0 && column.unique <= PIE_MAX_CLASSES
                        ? 'doughnut'
                        : 'bar',
                xColumn: column.name,
                aggregation: 'count',
                title: `Komposisi ${column.name}`,
            }),
        );
}

function scatterConfig(profile) {
    const pair = strongestPair(profile);

    if (!pair || Math.abs(pair.value) < 0.15) {
        return [];
    }

    return [
        emptyConfig({ type: 'scatter', xColumn: pair.x, yColumn: pair.y }),
    ];
}

function boxConfig(profile) {
    const columns = profile.numeric.slice(0, BOXPLOT_COLUMNS);

    return columns.length
        ? [emptyConfig({ type: 'box', columns: columns.map((c) => c.name) })]
        : [];
}

function heatmapConfig(profile) {
    const columns = profile.numeric.slice(0, 6);

    return columns.length >= 3
        ? [emptyConfig({ type: 'heatmap', columns: columns.map((c) => c.name) })]
        : [];
}

/** Konfigurasi panel otomatis untuk satu dataset yang sudah diprofiling. */
export function autoChartConfigs(profile, table) {
    return [
        ...timeConfigs(profile, table),
        ...histogramConfigs(profile),
        ...categoryConfigs(profile),
        ...scatterConfig(profile),
        ...boxConfig(profile),
        ...heatmapConfig(profile),
    ];
}
