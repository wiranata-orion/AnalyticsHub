import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { datasetPreview, datasets as placeholderDatasets } from '@/data/placeholder';

/*
 * Dataset aktif dibagikan lintas halaman.
 *
 * Profiling, Cleaning, Visualisasi, Mining, dan Machine Learning semuanya
 * beroperasi pada satu dataset yang sama. Tanpa store, tiap halaman menyimpan
 * pilihannya sendiri dan pengguna harus memilih ulang setiap berpindah menu.
 *
 * Saat REST API tersedia, `fetchAll()` diganti panggilan Axios — komponen yang
 * memakai store ini tidak perlu berubah.
 */
export const useDatasetStore = defineStore('dataset', () => {
    const items = ref(placeholderDatasets);
    const selectedId = ref(placeholderDatasets[0]?.id ?? null);
    const isLoading = ref(false);

    const selected = computed(
        () => items.value.find((item) => item.id === selectedId.value) ?? null,
    );

    const readyItems = computed(() =>
        items.value.filter((item) => item.status === 'ready'),
    );

    function select(id) {
        selectedId.value = Number(id);
    }

    /** Daftarkan dataset baru (hasil unggahan) di urutan teratas. */
    function add(payload) {
        const id = Math.max(0, ...items.value.map((item) => item.id)) + 1;
        const dataset = { id, ...payload };

        items.value = [dataset, ...items.value];

        return dataset;
    }

    function remove(id) {
        items.value = items.value.filter((item) => item.id !== Number(id));

        // Dataset aktif ikut terhapus? Pindah ke yang pertama tersisa.
        if (selectedId.value === Number(id)) {
            selectedId.value = items.value[0]?.id ?? null;
        }
    }

    function setStatus(id, status) {
        const dataset = items.value.find((item) => item.id === Number(id));

        if (dataset) {
            dataset.status = status;
        }
    }

    function findById(id) {
        return items.value.find((item) => item.id === Number(id)) ?? null;
    }

    /** Detail satu dataset beserta pratinjau isinya. */
    function detail(id) {
        const dataset = findById(id) ?? items.value[0];

        return {
            ...dataset,
            delimiter: ',',
            encoding: 'UTF-8',
            uploaded_by: 'Winata',
            preview: datasetPreview,
        };
    }

    return {
        items,
        selectedId,
        selected,
        readyItems,
        isLoading,
        select,
        add,
        remove,
        setStatus,
        findById,
        detail,
    };
});
