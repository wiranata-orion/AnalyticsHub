import axios from 'axios';

/*
 * Klien REST API AnalyticsHub.
 *
 * Semua analisis kini dikerjakan backend (Laravel + engine Python), jadi berkas
 * ini menggantikan perhitungan yang sebelumnya berjalan di peramban. Bentuk data
 * yang dikembalikan sudah disesuaikan dengan yang dipakai komponen — jadi
 * halaman cukup mengganti sumbernya, bukan cara menampilkannya.
 *
 * Kegagalan engine dikirim server sebagai 422 beserta pesan yang sudah dapat
 * dibaca pengguna; `unwrap` mengangkat pesan itu agar halaman tinggal
 * menampilkannya lewat toast tanpa menerjemahkan kode status sendiri.
 */
const client = axios.create({
    baseURL: '/api',
    headers: { Accept: 'application/json' },
    // AutoML dan forecasting bisa berjalan lebih dari satu menit pada dataset
    // besar; batas bawaan Axios akan memutusnya di tengah jalan.
    timeout: 600_000,
});

export class ApiError extends Error {
    constructor(message, status, details = null) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.details = details;
    }
}

async function unwrap(promise) {
    try {
        const response = await promise;

        return response.data;
    } catch (error) {
        if (error.response) {
            const { status, data } = error.response;

            throw new ApiError(
                data?.message ?? `Permintaan gagal dengan status ${status}.`,
                status,
                data?.errors ?? null,
            );
        }

        if (error.code === 'ECONNABORTED') {
            throw new ApiError(
                'Analisis melewati batas waktu. Coba pada dataset yang lebih kecil.',
                408,
            );
        }

        throw new ApiError(
            'Tidak dapat menghubungi server. Pastikan `php artisan serve` berjalan.',
            0,
        );
    }
}

export const api = {
    health: () => unwrap(client.get('/health')),

    datasets: {
        list: () => unwrap(client.get('/datasets')),
        show: (id) => unwrap(client.get(`/datasets/${id}`)),
        remove: (id) => unwrap(client.delete(`/datasets/${id}`)),
        reprofile: (id) => unwrap(client.post(`/datasets/${id}/profile`)),

        upload: (file, options = {}, onProgress = null) => {
            const form = new FormData();

            form.append('file', file);
            form.append('delimiter', options.delimiter ?? ',');
            form.append('encoding', options.encoding ?? 'UTF-8');
            form.append('has_header', options.hasHeader === false ? '0' : '1');

            return unwrap(
                client.post('/datasets', form, {
                    onUploadProgress: onProgress
                        ? (event) =>
                              onProgress(
                                  event.total
                                      ? Math.round((event.loaded / event.total) * 100)
                                      : 0,
                              )
                        : undefined,
                }),
            );
        },
    },

    cleaning: {
        show: (datasetId) => unwrap(client.get(`/datasets/${datasetId}/cleaning`)),
        apply: (datasetId, payload = {}) => unwrap(client.post(`/datasets/${datasetId}/cleaning`, payload)),
        downloadUrl: (datasetId) => `/api/datasets/${datasetId}/cleaning/download`,
    },

    /*
     * Satu pintu untuk seluruh analisis. `variant` mengikuti daftar di
     * App\Http\Controllers\Api\AnalysisController: univariate, bivariate,
     * multivariate, correlation, distribution, pairplot, missing_pattern,
     * feature_relationship, descriptive, inferential, clustering, classification,
     * regression, association, anomaly, timeseries, recommendation, insight,
     * quality, forecasting.
     */
    analysis: {
        run: (datasetId, variant, params = {}) =>
            unwrap(client.post(`/datasets/${datasetId}/analysis/${variant}`, params)),

        // Hasil terakhir tanpa menghitung ulang — dipakai saat halaman dibuka
        // kembali supaya analisis berat tidak dijalankan dua kali.
        latest: (datasetId, variant) =>
            unwrap(client.get(`/datasets/${datasetId}/analysis/${variant}`)),
    },

    features: {
        list: (datasetId) => unwrap(client.get(`/datasets/${datasetId}/feature-sets`)),
        create: (datasetId, payload) =>
            unwrap(client.post(`/datasets/${datasetId}/feature-sets`, payload)),
        selection: (datasetId, target, topK = 10) =>
            unwrap(
                client.post(`/datasets/${datasetId}/feature-selection`, {
                    target,
                    top_k: topK,
                }),
            ),
        remove: (id) => unwrap(client.delete(`/feature-sets/${id}`)),
    },

    models: {
        list: (datasetId = null) =>
            unwrap(
                client.get('/models', {
                    params: datasetId ? { dataset_id: datasetId } : {},
                }),
            ),
        show: (id) => unwrap(client.get(`/models/${id}`)),
        train: (datasetId, payload) =>
            unwrap(client.post(`/datasets/${datasetId}/models`, payload)),
        autoMl: (datasetId, payload) =>
            unwrap(client.post(`/datasets/${datasetId}/automl`, payload)),
        predict: (modelId, datasetId) =>
            unwrap(client.post(`/models/${modelId}/predict`, { dataset_id: datasetId })),
        explain: (modelId, methods = []) =>
            unwrap(client.post(`/models/${modelId}/explain`, { methods })),
        remove: (id) => unwrap(client.delete(`/models/${id}`)),
    },
};

export default api;
