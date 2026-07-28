import { ref } from 'vue';
import { defineStore } from 'pinia';

/*
 * Daftar grafik per dataset.
 *
 * Ditaruh di store, bukan di dalam halaman, karena dua alasan:
 *
 * 1. Grafik yang sudah disusun atau diubah pengguna harus tetap ada saat
 *    berpindah menu dan kembali lagi — di dalam komponen, seluruhnya hilang
 *    begitu halaman di-unmount.
 * 2. Disimpan per dataset, sehingga berganti dataset menampilkan susunan milik
 *    dataset itu sendiri, bukan mengosongkan pekerjaan sebelumnya.
 *
 * Isinya konfigurasi, bukan grafik jadi. Data grafiknya dihitung ulang saat
 * render, jadi susunan pengguna tetap benar meski barisnya berubah.
 */
export const useVisualizationStore = defineStore('visualization', () => {
    const boards = ref({});

    function board(datasetId) {
        return boards.value[Number(datasetId)] ?? null;
    }

    /** Isi susunan awal sekali saja; kunjungan berikutnya memakai yang tersimpan. */
    function ensure(datasetId, defaults) {
        const key = Number(datasetId);

        if (!boards.value[key]) {
            boards.value[key] = {
                nextId: defaults.length + 1,
                charts: defaults.map((config, index) => ({
                    id: index + 1,
                    config,
                })),
            };
        }

        return boards.value[key];
    }

    function charts(datasetId) {
        return board(datasetId)?.charts ?? [];
    }

    function add(datasetId, config) {
        const current = board(datasetId);

        if (!current) {
            return null;
        }

        const chart = { id: current.nextId, config };

        current.nextId += 1;
        current.charts.push(chart);

        return chart;
    }

    function update(datasetId, id, config) {
        const chart = board(datasetId)?.charts.find((item) => item.id === id);

        if (chart) {
            chart.config = config;
        }
    }

    function remove(datasetId, id) {
        const current = board(datasetId);

        if (current) {
            current.charts = current.charts.filter((item) => item.id !== id);
        }
    }

    /** Kembalikan ke susunan yang dipilihkan sistem dari hasil profiling. */
    function resetToAuto(datasetId, defaults) {
        delete boards.value[Number(datasetId)];

        return ensure(datasetId, defaults);
    }

    return { boards, ensure, charts, add, update, remove, resetToAuto };
});
