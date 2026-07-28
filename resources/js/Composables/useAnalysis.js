import { onMounted, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useDatasetStore } from '@/stores/dataset';
import { useToastStore } from '@/stores/toast';
import { api } from '@/Utils/api';

/*
 * Pola yang sama dipakai setiap halaman analisis:
 *
 *   1. saat dibuka, tampilkan hasil terakhir dari server bila ada — analisis
 *      yang sudah dijalankan tidak dihitung ulang hanya karena halaman dibuka
 *      kembali;
 *   2. tombol "jalankan" memanggil API, menandai sibuk, dan menyimpan hasilnya;
 *   3. kegagalan engine (422 beserta pesannya) ditampilkan lewat toast;
 *   4. berganti dataset mengulang langkah 1 untuk dataset itu.
 *
 * Ditaruh di composable supaya kesepuluh halaman tidak menyalin logika ini.
 */

/*
 * Hasil disimpan selama sesi, dikunci dataset + jenis analisis.
 *
 * Tanpa ini, berpindah menu selalu memulai permintaan baru dari keadaan kosong,
 * sehingga tulisan "Memuat…" berkedip sekejap padahal datanya sudah pernah
 * diambil. Dengan cache, kunjungan berikutnya tampil seketika dan penyegaran
 * berjalan diam-diam di belakang.
 */
const cache = new Map();

const cacheKey = (datasetId, variant) => `${datasetId}:${variant}`;

export function useAnalysis(variant, { autoLoad = true } = {}) {
    const datasetStore = useDatasetStore();
    const toast = useToastStore();
    const { selectedId } = storeToRefs(datasetStore);

    const result = ref(null);
    const meta = ref(null);
    const isRunning = ref(false);
    const isLoading = ref(false);

    function applyCache(datasetId) {
        const hit = cache.get(cacheKey(datasetId, variant));

        if (hit) {
            result.value = hit.data;
            meta.value = hit.meta;

            return true;
        }

        return false;
    }

    async function fetchLatest(datasetId, { silent = false } = {}) {
        if (!silent) {
            isLoading.value = true;
        }

        try {
            const response = await api.analysis.latest(datasetId, variant);

            // Dataset bisa saja sudah berganti saat permintaan ini selesai;
            // hasil yang datang terlambat tidak boleh menimpa layar dataset lain.
            if (datasetId !== selectedId.value) {
                return;
            }

            result.value = response.data;
            meta.value = response.meta;

            if (response.data) {
                cache.set(cacheKey(datasetId, variant), {
                    data: response.data,
                    meta: response.meta,
                });
            }
        } catch {
            // Hasil lama yang gagal dimuat bukan alasan menghalangi analisis baru.
            if (!silent) {
                result.value = null;
            }
        } finally {
            isLoading.value = false;
        }
    }

    async function loadLatest() {
        const datasetId = selectedId.value;

        if (!datasetId) {
            result.value = null;

            return;
        }

        // Ada di cache: tampilkan seketika, lalu segarkan tanpa status memuat.
        if (applyCache(datasetId)) {
            fetchLatest(datasetId, { silent: true });

            return;
        }

        await fetchLatest(datasetId);
    }

    async function run(params = {}) {
        const datasetId = selectedId.value;

        if (!datasetId) {
            toast.push('Pilih dataset terlebih dahulu.', 'warning');

            return null;
        }

        isRunning.value = true;

        try {
            const response = await api.analysis.run(datasetId, variant, params);

            result.value = response.data;
            meta.value = response.meta;
            cache.set(cacheKey(datasetId, variant), {
                data: response.data,
                meta: response.meta,
            });

            return response.data;
        } catch (error) {
            toast.push(error.message, 'warning');

            return null;
        } finally {
            isRunning.value = false;
        }
    }

    if (autoLoad) {
        // Cache dipakai sebelum render pertama supaya tidak ada kedipan sama
        // sekali saat berpindah menu.
        if (selectedId.value) {
            applyCache(selectedId.value);
        }

        onMounted(loadLatest);
        watch(selectedId, loadLatest);
    }

    return { datasetStore, toast, selectedId, result, meta, isRunning, isLoading, run, loadLatest };
}
