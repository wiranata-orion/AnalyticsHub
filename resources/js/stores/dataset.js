import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { api } from '@/Utils/api';

/*
 * Dataset aktif dibagikan lintas halaman.
 *
 * Profiling, EDA, statistik, mining, dan machine learning semuanya beroperasi
 * pada satu dataset yang sama. Tanpa store, tiap halaman menyimpan pilihannya
 * sendiri dan pengguna harus memilih ulang setiap berpindah menu.
 *
 * Sumber datanya kini REST API — daftar dari GET /api/datasets, detail kolom
 * (hasil profiling) dari GET /api/datasets/{id}. Detail di-cache per id karena
 * banyak halaman membutuhkannya untuk mengisi pilihan kolom.
 */
export const useDatasetStore = defineStore('dataset', () => {
    const items = ref([]);
    const selectedId = ref(null);
    const isLoading = ref(false);
    const loadError = ref(null);
    const details = ref({});

    const selected = computed(
        () => items.value.find((item) => String(item.id) === String(selectedId.value)) ?? null,
    );

    const readyItems = computed(() =>
        items.value.filter((item) => item.status === 'ready'),
    );

    /** Detail (termasuk kolom profiling) dataset terpilih, bila sudah dimuat. */
    const selectedDetail = computed(
        () => details.value[selectedId.value] ?? null,
    );

    const columns = computed(() => selectedDetail.value?.columns ?? []);

    async function fetchAll() {
        isLoading.value = true;
        loadError.value = null;

        try {
            const response = await api.datasets.list();

            items.value = response.data;

            // Pilihan sebelumnya dipertahankan bila datasetnya masih ada.
            if (!items.value.some((item) => item.id === selectedId.value)) {
                selectedId.value = readyItems.value[0]?.id ?? items.value[0]?.id ?? null;
            }

            if (selectedId.value) {
                await fetchDetail(selectedId.value);
            }
        } catch (error) {
            loadError.value = error.message;
        } finally {
            isLoading.value = false;
        }
    }

    async function fetchDetail(id, force = false) {
        if (!id) {
            return null;
        }

        const datasetId = String(id);

        if (!force && details.value[datasetId]) {
            return details.value[datasetId];
        }

        const response = await api.datasets.show(datasetId);

        details.value = { ...details.value, [datasetId]: response.data };

        return response.data;
    }

    async function select(id) {
        selectedId.value = id ? String(id) : null;
        await fetchDetail(selectedId.value);
    }

    async function remove(id) {
        const datasetId = String(id);

        await api.datasets.remove(datasetId);

        items.value = items.value.filter((item) => String(item.id) !== datasetId);
        delete details.value[datasetId];

        if (String(selectedId.value) === datasetId) {
            selectedId.value = items.value[0]?.id ?? null;

            if (selectedId.value) {
                await fetchDetail(selectedId.value);
            }
        }
    }

    async function upload(file, options, onProgress) {
        const response = await api.datasets.upload(file, options, onProgress);
        const dataset = response.data;

        details.value = { ...details.value, [dataset.id]: dataset };
        await fetchAll();
        selectedId.value = dataset.id;

        return dataset;
    }

    function findById(id) {
        const datasetId = String(id);

        return items.value.find((item) => String(item.id) === datasetId) ?? null;
    }

    return {
        items,
        selectedId,
        selected,
        selectedDetail,
        columns,
        readyItems,
        isLoading,
        loadError,
        details,
        fetchAll,
        fetchDetail,
        select,
        remove,
        upload,
        findById,
    };
});
