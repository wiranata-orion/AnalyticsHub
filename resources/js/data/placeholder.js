/*
 * Data sementara untuk fase pembangunan antarmuka.
 *
 * Belum ada API, sementara halaman perlu terisi agar tata letaknya bisa dinilai.
 * Bentuk objek di sini sengaja dibuat sama dengan yang nanti dikembalikan REST
 * API Laravel, sehingga saat backend siap cukup mengganti sumbernya di store
 * dengan panggilan Axios — komponen halaman tidak perlu diubah.
 *
 * Hapus berkas ini setelah endpoint asli tersedia.
 */

export const datasets = [
    { id: 1, name: 'penjualan_2026_q2.csv', format: 'CSV', rows: '128.400', columns: 17, size: '24,1 MB', status: 'ready', created_at: '27 Jul 2026', updated_at: '2 jam lalu' },
    { id: 2, name: 'pelanggan_segmentasi.xlsx', format: 'XLSX', rows: '42.980', columns: 24, size: '11,7 MB', status: 'processing', created_at: '27 Jul 2026', updated_at: '5 jam lalu' },
    { id: 3, name: 'sensor_iot_juli.csv', format: 'CSV', rows: '891.245', columns: 9, size: '86,3 MB', status: 'ready', created_at: '26 Jul 2026', updated_at: 'kemarin' },
    { id: 4, name: 'transaksi_gagal.csv', format: 'CSV', rows: '3.112', columns: 12, size: '1,4 MB', status: 'failed', created_at: '25 Jul 2026', updated_at: '2 hari lalu' },
    { id: 5, name: 'inventaris_gudang.xlsx', format: 'XLSX', rows: '15.660', columns: 21, size: '6,2 MB', status: 'ready', created_at: '24 Jul 2026', updated_at: '3 hari lalu' },
    { id: 6, name: 'log_akses_aplikasi.csv', format: 'CSV', rows: '2.310.887', columns: 8, size: '213,9 MB', status: 'ready', created_at: '22 Jul 2026', updated_at: '5 hari lalu' },
];

export const datasetPreview = {
    columns: ['id_transaksi', 'tanggal', 'wilayah', 'produk', 'jumlah', 'biaya_iklan', 'pendapatan'],
    types: ['integer', 'datetime', 'category', 'category', 'integer', 'float', 'float'],
    rows: [
        ['TRX-100241', '2026-04-02', 'Kalimantan Timur', 'Paket A', '12', '1250000', '4800000'],
        ['TRX-100242', '2026-04-02', 'Jawa Barat', 'Paket B', '5', '480000', '1950000'],
        ['TRX-100243', '2026-04-03', 'Sulawesi Selatan', 'Paket A', '21', '2100000', '8400000'],
        ['TRX-100244', '2026-04-03', 'Kalimantan Timur', 'Paket C', '3', '—', '1100000'],
        ['TRX-100245', '2026-04-04', 'Jawa Timur', 'Paket B', '9', '870000', '3510000'],
        ['TRX-100246', '2026-04-04', 'Bali', 'Paket A', '14', '1400000', '5600000'],
        ['TRX-100247', '2026-04-05', 'Jawa Barat', 'Paket C', '2', '190000', '740000'],
        ['TRX-100248', '2026-04-05', 'Kalimantan Timur', 'Paket B', '17', '1680000', '6630000'],
    ],
};

export const dashboard = {
    stats: [
        { label: 'Total Dataset', value: '24', icon: 'datasets', delta: 12.5, deltaLabel: 'vs bulan lalu' },
        { label: 'Baris Diproses', value: '3,42', unit: 'juta', icon: 'table', delta: 8.1, deltaLabel: 'vs bulan lalu' },
        { label: 'Analisis Berjalan', value: '5', icon: 'refresh', delta: null },
        { label: 'Rata-rata Missing', value: '2,8', unit: '%', icon: 'warning', delta: -1.4, deltaLabel: 'vs bulan lalu', lowerIsBetter: true },
    ],

    activityTrend: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul'],
        series: [
            { label: 'Dataset diunggah', data: [4, 6, 5, 9, 8, 12, 14] },
            { label: 'Analisis dijalankan', data: [7, 9, 12, 14, 16, 21, 26] },
        ],
    },

    jobDistribution: {
        labels: ['Profiling', 'Cleaning', 'Visualisasi', 'Mining', 'Machine Learning'],
        series: [{ label: 'Jumlah job', data: [38, 27, 19, 12, 9] }],
    },

    insights: [
        { tone: 'good', title: 'Korelasi kuat ditemukan', body: 'Kolom "biaya_iklan" dan "pendapatan" berkorelasi 0,87 pada penjualan_2026_q2.csv.' },
        { tone: 'warning', title: 'Missing value terkonsentrasi', body: 'Kolom "kode_pos" kosong pada 18,4% baris di pelanggan_segmentasi.xlsx.' },
        { tone: 'serious', title: 'Outlier terdeteksi', body: '312 baris sensor_iot_juli.csv berada di luar 3 simpangan baku pada kolom "suhu".' },
    ],
};

export const profiling = {
    summary: [
        { label: 'Jumlah Baris', value: '128.400', icon: 'table' },
        { label: 'Jumlah Kolom', value: '17', icon: 'datasets' },
        { label: 'Sel Kosong', value: '3,6', unit: '%', icon: 'warning' },
        { label: 'Baris Duplikat', value: '284', icon: 'document' },
    ],

    columns: [
        { name: 'id_transaksi', type: 'integer', missing: 0.0, unique: 128400, mean: '—', std: '—', outliers: 0 },
        { name: 'tanggal', type: 'datetime', missing: 0.0, unique: 91, mean: '—', std: '—', outliers: 0 },
        { name: 'wilayah', type: 'category', missing: 1.2, unique: 34, mean: '—', std: '—', outliers: 0 },
        { name: 'produk', type: 'category', missing: 0.0, unique: 3, mean: '—', std: '—', outliers: 0 },
        { name: 'jumlah', type: 'integer', missing: 0.4, unique: 87, mean: '10,4', std: '6,1', outliers: 143 },
        { name: 'biaya_iklan', type: 'float', missing: 8.7, unique: 12044, mean: '1.043.220', std: '612.400', outliers: 219 },
        { name: 'pendapatan', type: 'float', missing: 0.1, unique: 41880, mean: '4.118.900', std: '2.340.100', outliers: 312 },
        { name: 'kode_pos', type: 'category', missing: 18.4, unique: 1206, mean: '—', std: '—', outliers: 0 },
    ],

    missingByColumn: {
        labels: ['kode_pos', 'biaya_iklan', 'wilayah', 'jumlah', 'pendapatan'],
        series: [{ label: 'Missing', data: [18.4, 8.7, 1.2, 0.4, 0.1] }],
    },

    typeDistribution: {
        labels: ['Numerik', 'Kategori', 'Tanggal', 'Teks'],
        series: [{ label: 'Kolom', data: [7, 6, 2, 2] }],
    },

    correlation: {
        columns: ['jumlah', 'biaya_iklan', 'pendapatan', 'diskon', 'retur'],
        matrix: [
            [1.0, 0.62, 0.78, -0.14, -0.31],
            [0.62, 1.0, 0.87, 0.09, -0.12],
            [0.78, 0.87, 1.0, -0.22, -0.45],
            [-0.14, 0.09, -0.22, 1.0, 0.38],
            [-0.31, -0.12, -0.45, 0.38, 1.0],
        ],
    },
};

export const cleaning = {
    issues: [
        { key: 'missing', title: 'Missing Value', count: 4612, unit: 'sel', tone: 'warning', icon: 'warning', description: 'Tersebar di 5 kolom, terbanyak pada "kode_pos".' },
        { key: 'duplicate', title: 'Baris Duplikat', count: 284, unit: 'baris', tone: 'serious', icon: 'document', description: 'Duplikat penuh pada seluruh kolom.' },
        { key: 'outlier', title: 'Outlier', count: 674, unit: 'baris', tone: 'serious', icon: 'trendUp', description: 'Metode IQR pada 3 kolom numerik.' },
        { key: 'type', title: 'Tipe Data Tidak Cocok', count: 2, unit: 'kolom', tone: 'critical', icon: 'table', description: 'Kolom "tanggal" dan "jumlah" terbaca sebagai teks.' },
    ],

    strategies: [
        { key: 'missing', label: 'Penanganan Missing Value', options: ['Hapus baris', 'Isi dengan mean', 'Isi dengan median', 'Isi dengan modus', 'Forward fill'], selected: 'Isi dengan median' },
        { key: 'duplicate', label: 'Penanganan Duplikat', options: ['Hapus semua duplikat', 'Simpan kemunculan pertama', 'Simpan kemunculan terakhir', 'Biarkan'], selected: 'Simpan kemunculan pertama' },
        { key: 'outlier', label: 'Penanganan Outlier', options: ['Biarkan', 'Hapus (IQR)', 'Hapus (Z-Score)', 'Winsorize'], selected: 'Winsorize' },
        { key: 'encoding', label: 'Encoding Kolom Kategori', options: ['Tidak ada', 'Label Encoding', 'One-Hot Encoding', 'Ordinal Encoding'], selected: 'One-Hot Encoding' },
    ],

    impact: {
        labels: ['Sebelum', 'Sesudah'],
        series: [
            { label: 'Baris valid', data: [123504, 127832] },
            { label: 'Baris bermasalah', data: [4896, 568] },
        ],
    },
};

export const visualization = {
    revenueByRegion: {
        labels: ['Kaltim', 'Jabar', 'Jatim', 'Sulsel', 'Bali', 'Sumut'],
        series: [{ label: 'Pendapatan (juta)', data: [842, 671, 588, 431, 366, 298] }],
    },

    monthlyTrend: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul'],
        series: [
            { label: 'Paket A', data: [120, 138, 145, 162, 171, 189, 204] },
            { label: 'Paket B', data: [98, 104, 96, 118, 126, 131, 142] },
            { label: 'Paket C', data: [45, 52, 61, 58, 67, 74, 81] },
        ],
    },

    distribution: {
        labels: ['0–5', '6–10', '11–15', '16–20', '21–25', '26–30', '31+'],
        series: [{ label: 'Frekuensi', data: [8420, 21340, 34980, 28110, 16720, 9840, 4210] }],
    },

    // Dibatasi 3 seri: pada scatter semua pasangan warna bersanding sekaligus,
    // dan hanya tiga slot pertama palet yang lolos gate semua-pasangan.
    scatter: {
        series: [
            { label: 'Paket A', data: [{ x: 12, y: 48 }, { x: 21, y: 84 }, { x: 14, y: 56 }, { x: 17, y: 66 }, { x: 9, y: 35 }, { x: 24, y: 95 }, { x: 19, y: 74 }] },
            { label: 'Paket B', data: [{ x: 5, y: 19 }, { x: 9, y: 35 }, { x: 7, y: 26 }, { x: 12, y: 44 }, { x: 15, y: 58 }, { x: 4, y: 14 }, { x: 11, y: 41 }] },
            { label: 'Paket C', data: [{ x: 3, y: 11 }, { x: 2, y: 7 }, { x: 6, y: 22 }, { x: 4, y: 15 }, { x: 8, y: 29 }, { x: 5, y: 18 }, { x: 7, y: 25 }] },
        ],
    },

    composition: {
        labels: ['Paket A', 'Paket B', 'Paket C'],
        series: [{ label: 'Pangsa', data: [48, 33, 19] }],
    },
};

export const mining = {
    algorithms: [
        { key: 'clustering', name: 'Clustering', icon: 'mining', description: 'Kelompokkan baris serupa tanpa label. K-Means, DBSCAN, Hierarchical.', runs: 12 },
        { key: 'classification', name: 'Classification', icon: 'profiling', description: 'Prediksi label kategori. Decision Tree, Random Forest, Naive Bayes.', runs: 8 },
        { key: 'regression', name: 'Regression', icon: 'trendUp', description: 'Prediksi nilai kontinu. Linear, Ridge, Gradient Boosting.', runs: 6 },
        { key: 'association', name: 'Association Rule', icon: 'datasets', description: 'Temukan pola "yang dibeli bersama". Apriori, FP-Growth.', runs: 4 },
        { key: 'anomaly', name: 'Anomaly Detection', icon: 'warning', description: 'Deteksi baris menyimpang. Isolation Forest, LOF.', runs: 5 },
        { key: 'timeseries', name: 'Time Series', icon: 'visualization', description: 'Analisis dan proyeksi deret waktu. ARIMA, Prophet.', runs: 3 },
    ],

    clusterPreview: {
        series: [
            { label: 'Cluster 1', data: [{ x: 12, y: 48 }, { x: 14, y: 56 }, { x: 11, y: 44 }, { x: 15, y: 52 }, { x: 13, y: 50 }] },
            { label: 'Cluster 2', data: [{ x: 32, y: 22 }, { x: 35, y: 26 }, { x: 30, y: 19 }, { x: 34, y: 24 }, { x: 33, y: 21 }] },
            { label: 'Cluster 3', data: [{ x: 22, y: 82 }, { x: 25, y: 88 }, { x: 21, y: 79 }, { x: 24, y: 85 }, { x: 23, y: 91 }] },
        ],
    },

    associationRules: [
        { id: 1, antecedent: 'Paket A', consequent: 'Add-on Garansi', support: '0,142', confidence: '0,681', lift: '2,41' },
        { id: 2, antecedent: 'Paket B, Instalasi', consequent: 'Add-on Garansi', support: '0,098', confidence: '0,624', lift: '2,21' },
        { id: 3, antecedent: 'Paket C', consequent: 'Pelatihan', support: '0,076', confidence: '0,559', lift: '1,98' },
        { id: 4, antecedent: 'Add-on Garansi', consequent: 'Perpanjangan', support: '0,064', confidence: '0,512', lift: '1,81' },
    ],
};

export const machineLearning = {
    models: [
        { id: 1, name: 'Prediksi Churn Pelanggan', algorithm: 'Random Forest', target: 'churn', metric: 'Akurasi', score: '91,4%', status: 'ready', trained_at: '27 Jul 2026' },
        { id: 2, name: 'Estimasi Pendapatan', algorithm: 'Gradient Boosting', target: 'pendapatan', metric: 'R²', score: '0,873', status: 'ready', trained_at: '26 Jul 2026' },
        { id: 3, name: 'Segmentasi Pelanggan', algorithm: 'K-Means (k=4)', target: '—', metric: 'Silhouette', score: '0,612', status: 'training', trained_at: '27 Jul 2026' },
        { id: 4, name: 'Deteksi Transaksi Janggal', algorithm: 'Isolation Forest', target: '—', metric: 'Presisi', score: '0,784', status: 'failed', trained_at: '25 Jul 2026' },
    ],

    featureImportance: {
        labels: ['tenure', 'biaya_bulanan', 'jumlah_komplain', 'metode_bayar', 'durasi_kontrak', 'usia'],
        series: [{ label: 'Kontribusi', data: [0.28, 0.22, 0.17, 0.13, 0.11, 0.09] }],
    },

    learningCurve: {
        labels: ['10%', '25%', '40%', '55%', '70%', '85%', '100%'],
        series: [
            { label: 'Akurasi latih', data: [0.82, 0.87, 0.9, 0.92, 0.93, 0.94, 0.95] },
            { label: 'Akurasi validasi', data: [0.74, 0.8, 0.84, 0.87, 0.89, 0.9, 0.91] },
        ],
    },

    confusionMatrix: {
        labels: ['Bertahan', 'Churn'],
        matrix: [
            [8420, 312],
            [486, 1982],
        ],
    },

    evaluation: [
        { label: 'Akurasi', value: '91,4%' },
        { label: 'Presisi', value: '86,4%' },
        { label: 'Recall', value: '80,3%' },
        { label: 'F1-Score', value: '83,2%' },
        { label: 'ROC-AUC', value: '0,943' },
        { label: 'Data Latih', value: '80%' },
        { label: 'Data Uji', value: '20%' },
        { label: 'Waktu Latih', value: '42 dtk' },
    ],
};

export const reports = [
    { id: 1, title: 'Laporan Profiling — Penjualan Q2 2026', dataset: 'penjualan_2026_q2.csv', type: 'Profiling', format: 'PDF', size: '1,8 MB', status: 'ready', created_at: '27 Jul 2026' },
    { id: 2, title: 'Ringkasan Segmentasi Pelanggan', dataset: 'pelanggan_segmentasi.xlsx', type: 'Data Mining', format: 'PDF', size: '2,4 MB', status: 'ready', created_at: '26 Jul 2026' },
    { id: 3, title: 'Evaluasi Model Churn', dataset: 'pelanggan_segmentasi.xlsx', type: 'Machine Learning', format: 'XLSX', size: '640 KB', status: 'generating', created_at: '27 Jul 2026' },
    { id: 4, title: 'Analisis Anomali Sensor IoT', dataset: 'sensor_iot_juli.csv', type: 'Anomaly Detection', format: 'PDF', size: '3,1 MB', status: 'ready', created_at: '24 Jul 2026' },
];
