/*
 * Sumber kebenaran warna untuk chart (Chart.js tidak bisa membaca kelas Tailwind).
 *
 * Nilai di sini WAJIB identik dengan `tailwind.config.js`. Set warna sudah lolos
 * validasi colorblind-safe pada permukaan terang (#fcfcfb) dan gelap (#1a1a19):
 * pisah CVD terburuk antar-slot bersebelahan 9.1 (light) / 8.4 (dark).
 *
 * Aturan pakai:
 * - Ambil slot BERURUTAN mulai dari indeks 0. Jangan diputar, jangan diacak.
 * - Warna mengikuti entitas, bukan peringkat — filter yang mengubah jumlah seri
 *   tidak boleh mengecat ulang seri yang tersisa.
 * - Untuk scatter/bubble (semua pasangan warna saling berdekatan di layar),
 *   batasi maksimal 3 seri; sisanya lipat ke "Lainnya" atau pakai small multiples.
 */

export const SCATTER_SERIES_LIMIT = 3;

const LIGHT = {
    surface: '#fcfcfb',
    plane: '#f9f9f7',
    ink: '#0b0b0b',
    inkSecondary: '#52514e',
    muted: '#898781',
    grid: '#e1e0d9',
    axis: '#c3c2b7',
    series: [
        '#2a78d6',
        '#eb6834',
        '#1baf7a',
        '#eda100',
        '#e87ba4',
        '#008300',
        '#4a3aa7',
        '#e34948',
    ],
    // Biru terang -> gelap, untuk besaran kontinu (heatmap korelasi).
    sequential: [
        '#cde2fb',
        '#b7d3f6',
        '#9ec5f4',
        '#86b6ef',
        '#6da7ec',
        '#5598e7',
        '#3987e5',
        '#2a78d6',
        '#256abf',
        '#1c5cab',
        '#184f95',
        '#104281',
        '#0d366b',
    ],
    divergingMid: '#f0efec',
};

const DARK = {
    surface: '#1a1a19',
    plane: '#0d0d0d',
    ink: '#ffffff',
    inkSecondary: '#c3c2b7',
    muted: '#898781',
    grid: '#2c2c2a',
    axis: '#383835',
    series: [
        '#3987e5',
        '#d95926',
        '#199e70',
        '#c98500',
        '#d55181',
        '#008300',
        '#9085e9',
        '#e66767',
    ],
    sequential: LIGHT.sequential,
    divergingMid: '#383835',
};

// Status tidak pernah berganti antar tema — keempat langkah ini lolos 3:1 pada
// permukaan gelap dan dipasangkan ikon + label agar warna tak pernah berdiri sendiri.
export const STATUS = {
    good: '#0ca30c',
    warning: '#fab219',
    serious: '#ec835a',
    critical: '#d03b3b',
};

export function palette(isDark) {
    return isDark ? DARK : LIGHT;
}

/** Ambil `count` warna seri berurutan dari slot pertama. */
export function seriesColors(isDark, count) {
    return palette(isDark).series.slice(0, count);
}

/**
 * Petakan nilai 0..1 ke ramp biru sekuensial (besaran kontinu tanpa polaritas).
 */
export function sequentialAt(ratio) {
    const ramp = LIGHT.sequential;
    const clamped = Math.min(Math.max(ratio, 0), 1);

    return ramp[Math.round(clamped * (ramp.length - 1))];
}

/*
 * Skala diverging untuk korelasi.
 *
 * Korelasi punya titik nol bermakna dan dua kutub berlawanan, jadi skalanya
 * BUKAN sekuensial: dua rona (biru = positif, merah = negatif) bertemu di abu
 * netral. Abu di tengah penting — kalau midpoint-nya berona, "tidak ada
 * korelasi" akan terbaca sebagai sesuatu.
 */
const DIVERGING = {
    positive: '#0d366b',
    negative: '#8c1f1f',
    mid: { light: '#f0efec', dark: '#383835' },
};

function hexToRgb(hex) {
    const value = parseInt(hex.slice(1), 16);

    return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

function mix(fromHex, toHex, ratio) {
    const from = hexToRgb(fromHex);
    const to = hexToRgb(toHex);
    const channel = (index) =>
        Math.round(from[index] + (to[index] - from[index]) * ratio);

    return `rgb(${channel(0)}, ${channel(1)}, ${channel(2)})`;
}

/** Petakan koefisien -1..1 ke warna diverging. */
export function divergingAt(value, isDark) {
    const mid = isDark ? DIVERGING.mid.dark : DIVERGING.mid.light;
    const magnitude = Math.min(Math.abs(value), 1);
    const pole = value >= 0 ? DIVERGING.positive : DIVERGING.negative;

    return mix(mid, pole, magnitude);
}

/**
 * Teks di atas sel diverging: putih hanya setelah selnya cukup gelap.
 * Angka pada sel SELALU dicetak, jadi warna tak pernah jadi satu-satunya isyarat.
 */
export function divergingInk(value, isDark) {
    const magnitude = Math.abs(value);

    if (magnitude >= 0.55) {
        return '#ffffff';
    }

    return isDark ? '#c3c2b7' : '#0b0b0b';
}
