/*
 * Titik masuk tunggal ke data + hasil profiling sebuah dataset.
 *
 * Profiling menyapu seluruh baris, jadi hasilnya di-cache per dataset: halaman
 * Visualisasi, Data Mining, dan Machine Learning memakai objek yang sama dan
 * angka di ketiganya dijamin konsisten.
 *
 * Saat REST API tersedia, fungsi ini yang berubah menjadi pemanggilan
 * `GET /api/datasets/{id}/profile` — pemakainya tidak perlu ikut diubah.
 */

import { datasetTable } from '@/data/profiles';
import { profileTable } from '@/Utils/profiler';

const cache = new Map();

export function datasetAnalysis(id) {
    const key = Number(id);

    if (!cache.has(key)) {
        const table = datasetTable(key);

        cache.set(key, { table, profile: profileTable(table) });
    }

    return cache.get(key);
}
