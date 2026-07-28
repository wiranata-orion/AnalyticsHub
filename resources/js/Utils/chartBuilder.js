/*
 * Pembangun grafik: satu konfigurasi -> satu panel siap render.
 *
 * Seluruh grafik di halaman Visualisasi melewati fungsi ini, baik yang dipilihkan
 * sistem setelah profiling maupun yang disusun sendiri oleh pengguna. Karena
 * bentuk konfigurasinya sama, grafik otomatis pun bisa langsung dibuka dan
 * diubah — tidak perlu ada dua jenis visualisasi yang terpisah.
 *
 * Pengelompokan dan agregasinya berjalan atas baris dataset sungguhan, sehingga
 * logika di sini tetap berlaku saat sumber barisnya diganti REST API.
 */

import { formatNumber, isNumericType, pearson, quantile } from '@/Utils/profiler';
import { SCATTER_SERIES_LIMIT } from '@/Utils/palette';

export const CHART_TYPES = [
    { value: 'bar', label: 'Batang' },
    { value: 'line', label: 'Garis' },
    { value: 'area', label: 'Area' },
    { value: 'doughnut', label: 'Donat' },
    { value: 'scatter', label: 'Scatter' },
    { value: 'box', label: 'Boxplot' },
    { value: 'heatmap', label: 'Heatmap Korelasi' },
];

// Boxplot dan heatmap membaca beberapa kolom numerik sekaligus, bukan sepasang
// sumbu — formulir menyembunyikan medan sumbu X/Y untuk kedua jenis ini.
export const MULTI_COLUMN_TYPES = ['box', 'heatmap'];

export const AGGREGATIONS = [
    { value: 'sum', label: 'Jumlah (sum)' },
    { value: 'avg', label: 'Rata-rata' },
    { value: 'median', label: 'Median' },
    { value: 'max', label: 'Maksimum' },
    { value: 'min', label: 'Minimum' },
    { value: 'count', label: 'Hitung baris' },
];

export const TIME_GRAINS = [
    { value: 'day', label: 'Harian' },
    { value: 'month', label: 'Bulanan' },
];

export function aggregate(values, kind) {
    if (kind === 'count') {
        return values.length;
    }

    const numbers = values.filter((value) => Number.isFinite(value));

    if (!numbers.length) {
        return 0;
    }

    switch (kind) {
        case 'avg':
            return numbers.reduce((sum, value) => sum + value, 0) / numbers.length;
        case 'median':
            return quantile([...numbers].sort((a, b) => a - b), 0.5);
        case 'max':
            return Math.max(...numbers);
        case 'min':
            return Math.min(...numbers);
        default:
            return numbers.reduce((sum, value) => sum + value, 0);
    }
}

/** Kunci pengelompokan untuk kolom waktu: 'YYYY-MM-DD' atau 'YYYY-MM'. */
export function dateKey(value, grain) {
    if (!value) {
        return null;
    }

    const day = String(value).slice(0, 10);

    return grain === 'month' ? day.slice(0, 7) : day;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];

export function dateLabel(key, grain) {
    const [year, month, day] = key.split('-');

    return grain === 'month'
        ? `${MONTHS[Number(month) - 1]} ${year}`
        : `${Number(day)} ${MONTHS[Number(month) - 1]}`;
}

/** Rentang waktu panjang lebih terbaca per bulan daripada per hari. */
export function suggestGrain(values) {
    const times = values
        .filter(Boolean)
        .map((value) => new Date(String(value).slice(0, 10)).getTime())
        .filter(Number.isFinite);

    if (times.length < 2) {
        return 'day';
    }

    const spanDays = (Math.max(...times) - Math.min(...times)) / 86_400_000;

    return spanDays > 120 ? 'month' : 'day';
}

/** Rata-rata bergerak; jendelanya menyesuaikan panjang seri. */
export function movingAverage(values) {
    const window = Math.max(3, Math.round(values.length / 8));

    return {
        window,
        data: values.map((_, index) =>
            Number(
                aggregate(
                    values.slice(Math.max(0, index - window + 1), index + 1),
                    'avg',
                ).toFixed(2),
            ),
        ),
    };
}

/*
 * Kolom numerik pada sumbu X dijadikan rentang, bukan nilai satuan — tanpa ini
 * sumbu kategori akan berisi ratusan label unik dan grafiknya tidak terbaca.
 * Inilah yang membuat "histogram" cukup dinyatakan sebagai grafik batang dengan
 * sumbu X numerik dan agregasi hitung baris.
 */
function numericBinner(rows, column) {
    const values = rows.map((row) => Number(row[column])).filter(Number.isFinite);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const binCount = 8;
    const width = (max - min) / binCount || 1;

    return (value) => {
        if (!Number.isFinite(Number(value))) {
            return null;
        }

        const index = Math.min(binCount - 1, Math.floor((Number(value) - min) / width));
        const from = min + index * width;

        return {
            key: String(index).padStart(2, '0'),
            label: `${formatNumber(from)}–${formatNumber(from + width)}`,
        };
    };
}

function applyFilter(rows, config) {
    if (!config.filterColumn || !config.filterValue) {
        return rows;
    }

    return rows.filter(
        (row) => String(row[config.filterColumn]) === String(config.filterValue),
    );
}

const columnMeta = (profile, name) =>
    profile.columns.find((column) => column.name === name) ?? null;

export function aggregationLabel(config) {
    if (config.aggregation === 'count') {
        return 'Jumlah baris';
    }

    const aggregation = AGGREGATIONS.find(
        (item) => item.value === config.aggregation,
    );

    return `${aggregation?.label ?? ''} ${config.yColumn}`.trim();
}

/** Judul bawaan bila pengguna tidak mengisi judul sendiri. */
export function defaultTitle(config) {
    if (config.type === 'box') {
        return 'Ringkasan Lima Angka';
    }

    if (config.type === 'heatmap') {
        return 'Matriks Korelasi';
    }

    if (config.type === 'scatter') {
        return `${config.yColumn} terhadap ${config.xColumn}`;
    }

    return `${aggregationLabel(config)} per ${config.xColumn}`;
}

function describe(config, chart) {
    if (config.type === 'box') {
        return 'Boxplot — median, kuartil, dan nilai ekstrem per kolom';
    }

    if (config.type === 'heatmap') {
        return 'Koefisien Pearson antar kolom numerik';
    }

    return [
        config.type === 'scatter'
            ? 'Scatter plot'
            : `Sumbu X: ${config.xColumn}`,
        config.colorColumn ? `warna: ${config.colorColumn}` : null,
        config.filterColumn && config.filterValue
            ? `filter: ${config.filterColumn} = ${config.filterValue}`
            : null,
        chart?.smoothWindow
            ? `rata-rata bergerak ${chart.smoothWindow} periode`
            : null,
    ]
        .filter(Boolean)
        .join(' · ');
}

// ---------------------------------------------------------------------------
// Jenis grafik
// ---------------------------------------------------------------------------

function buildBox(profile, config) {
    const columns = (config.columns ?? [])
        .map((name) => columnMeta(profile, name))
        .filter((column) => column && isNumericType(column.type));

    if (!columns.length) {
        return { ok: false, message: 'Pilih minimal satu kolom numerik untuk boxplot.' };
    }

    return {
        ok: true,
        chart: {
            render: 'box',
            boxes: columns.map((column) => ({
                label: column.name,
                min: column.min,
                q1: column.q1,
                median: column.median,
                q3: column.q3,
                max: column.max,
                lowerFence: column.lowerFence,
                upperFence: column.upperFence,
                outlierCount: column.outlierCount,
            })),
        },
    };
}

function buildHeatmap(table, profile, config) {
    const names = (config.columns ?? []).filter((name) => {
        const column = columnMeta(profile, name);

        return column && isNumericType(column.type);
    });

    if (names.length < 2) {
        return {
            ok: false,
            message: 'Heatmap korelasi butuh minimal dua kolom numerik.',
        };
    }

    const series = names.map((name) =>
        table.rows.map((row) => (row[name] === null ? NaN : Number(row[name]))),
    );

    return {
        ok: true,
        chart: {
            render: 'heatmap',
            columns: names,
            matrix: series.map((left) =>
                series.map((right) => Number(pearson(left, right).toFixed(2))),
            ),
        },
    };
}

function buildScatter(rows, config, xMeta, yMeta) {
    if (!isNumericType(xMeta.type) || !yMeta) {
        return {
            ok: false,
            message: 'Scatter membutuhkan kolom numerik pada sumbu X dan sumbu Y.',
        };
    }

    const points = rows
        .filter(
            (row) =>
                Number.isFinite(Number(row[config.xColumn])) &&
                Number.isFinite(Number(row[config.yColumn])),
        )
        .map((row) => ({
            x: Number(row[config.xColumn]),
            y: Number(row[config.yColumn]),
            group: config.colorColumn ? String(row[config.colorColumn]) : null,
        }));

    if (!config.colorColumn) {
        return {
            ok: true,
            chart: {
                render: 'panel',
                type: 'scatter',
                labels: [],
                series: [
                    { label: `${config.yColumn} vs ${config.xColumn}`, data: points },
                ],
            },
        };
    }

    // Pada scatter semua pasangan warna bersanding sekaligus; palet hanya
    // menjamin keterbedaan sampai tiga slot pertama.
    const all = [...new Set(points.map((point) => point.group))];
    const groups = all.slice(0, SCATTER_SERIES_LIMIT);

    return {
        ok: true,
        chart: {
            render: 'panel',
            type: 'scatter',
            labels: [],
            series: groups.map((group) => ({
                label: group,
                data: points.filter((point) => point.group === group),
            })),
            note:
                groups.length < all.length
                    ? `Ditampilkan ${groups.length} kelompok pertama agar warna tetap terbedakan.`
                    : null,
        },
    };
}

function buildGrouped(rows, config, xMeta) {
    const grain = config.timeGrain ?? 'day';
    const binner = isNumericType(xMeta.type)
        ? numericBinner(rows, config.xColumn)
        : null;

    const keyOf = (row) => {
        const raw = row[config.xColumn];

        if (raw === null || raw === undefined) {
            return null;
        }

        if (xMeta.type === 'datetime') {
            const key = dateKey(raw, grain);

            return key ? { key, label: dateLabel(key, grain) } : null;
        }

        return binner ? binner(raw) : { key: String(raw), label: String(raw) };
    };

    const labelByKey = new Map();
    const buckets = new Map();
    const groupNames = new Set();

    for (const row of rows) {
        const bucket = keyOf(row);

        if (!bucket) {
            continue;
        }

        labelByKey.set(bucket.key, bucket.label);

        const group = config.colorColumn
            ? String(row[config.colorColumn] ?? '—')
            : 'total';

        groupNames.add(group);

        const cell = `${bucket.key}|${group}`;

        if (!buckets.has(cell)) {
            buckets.set(cell, []);
        }

        buckets
            .get(cell)
            .push(config.aggregation === 'count' ? 1 : Number(row[config.yColumn]));
    }

    if (!buckets.size) {
        return { ok: false, message: 'Tidak ada nilai yang bisa dikelompokkan.' };
    }

    let keys = [...labelByKey.keys()];
    const ordered = xMeta.type === 'datetime' || binner;

    if (ordered) {
        keys.sort();
    } else {
        // Kategori diurutkan dari yang terbesar dan dipangkas, supaya batang
        // panjang tidak tenggelam di antara puluhan kategori kecil.
        const totals = new Map(
            keys.map((key) => [
                key,
                aggregate(
                    [...groupNames].flatMap(
                        (group) => buckets.get(`${key}|${group}`) ?? [],
                    ),
                    config.aggregation,
                ),
            ]),
        );

        keys.sort((a, b) => totals.get(b) - totals.get(a));
        keys = keys.slice(0, 12);
    }

    const series = [...groupNames].slice(0, 8).map((group) => ({
        label: group === 'total' ? aggregationLabel(config) : group,
        data: keys.map((key) =>
            Number(
                aggregate(
                    buckets.get(`${key}|${group}`) ?? [],
                    config.aggregation,
                ).toFixed(2),
            ),
        ),
    }));

    let smoothWindow = null;

    // Rata-rata bergerak hanya masuk akal pada sumbu yang berurutan; pada
    // kategori, urutan batang tidak punya arti sehingga garisnya menyesatkan.
    if (config.smooth && ordered && series.length === 1) {
        const smoothed = movingAverage(series[0].data);

        smoothWindow = smoothed.window;
        series.push({
            label: `Rata-rata bergerak ${smoothed.window} periode`,
            data: smoothed.data,
        });
    }

    return {
        ok: true,
        chart: {
            render: 'panel',
            type: config.type,
            labels: keys.map((key) => labelByKey.get(key)),
            series,
            smoothWindow,
            // Batang horizontal saat labelnya berupa nama kategori panjang.
            horizontal:
                config.type === 'bar' &&
                xMeta.type === 'category' &&
                !config.colorColumn,
        },
    };
}

/**
 * @returns {{ ok: true, chart: {...}, title, subtitle } | { ok: false, message }}
 */
export function buildChart(table, profile, config) {
    const outcome = compute(table, profile, config);

    if (!outcome.ok) {
        return outcome;
    }

    return {
        ...outcome,
        title: config.title?.trim() || defaultTitle(config),
        subtitle: describe(config, outcome.chart),
    };
}

function compute(table, profile, config) {
    if (config.type === 'box') {
        return buildBox(profile, config);
    }

    if (config.type === 'heatmap') {
        return buildHeatmap(table, profile, config);
    }

    const rows = applyFilter(table.rows, config);

    if (!rows.length) {
        return { ok: false, message: 'Filter tidak menyisakan baris untuk digambar.' };
    }

    const xMeta = columnMeta(profile, config.xColumn);

    if (!xMeta) {
        return { ok: false, message: 'Pilih kolom untuk sumbu X.' };
    }

    const needsY = config.aggregation !== 'count' || config.type === 'scatter';
    const yMeta = needsY ? columnMeta(profile, config.yColumn) : null;

    if (needsY && (!yMeta || !isNumericType(yMeta.type))) {
        return {
            ok: false,
            message:
                'Sumbu Y harus kolom numerik, atau gunakan agregasi "Hitung baris".',
        };
    }

    return config.type === 'scatter'
        ? buildScatter(rows, config, xMeta, yMeta)
        : buildGrouped(rows, config, xMeta);
}
