import { markRaw, ref } from 'vue';
import { defineStore } from 'pinia';

/*
 * Pilihan algoritma dan hasil analisis per dataset.
 *
 * Menjalankan analisis butuh waktu dan perhatian pengguna; hasilnya tidak boleh
 * hilang hanya karena berpindah ke menu lain untuk memeriksa sesuatu. Disimpan
 * per dataset agar berganti dataset tidak menghapus hasil dataset sebelumnya.
 *
 * Muatan hasil disimpan `markRaw` — isinya hanya dibaca untuk dirender, jadi
 * memproksikan seluruh larik titik dan baris tabel ke sistem reaktif tidak ada
 * gunanya dan membuat setiap akses lebih mahal.
 */
export const useMiningStore = defineStore('mining', () => {
    const sessions = ref({});

    // Sesi baru dimulai tanpa algoritma terpilih: yang dijalankan harus selalu
    // hasil pilihan pengguna, bukan pilihan yang sudah tercentang sejak awal.
    function session(datasetId) {
        const key = Number(datasetId);

        if (!sessions.value[key]) {
            sessions.value[key] = { selected: [], results: [] };
        }

        return sessions.value[key];
    }

    function setSelection(datasetId, keys) {
        session(datasetId).selected = [...keys];
    }

    function setResults(datasetId, results) {
        session(datasetId).results = results.map((result) =>
            result.payload
                ? { ...result, payload: markRaw(result.payload) }
                : result,
        );
    }

    return { sessions, session, setSelection, setResults };
});
