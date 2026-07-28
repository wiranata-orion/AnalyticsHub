/*
 * Isi baris dataset untuk fase pembangunan antarmuka.
 *
 * Halaman Visualisasi, Data Mining, dan Machine Learning menghitung hasilnya dari
 * baris sungguhan — profiling, k-means, naive bayes, apriori, dan seterusnya
 * berjalan di peramban. Karena REST API belum ada, barisnya dibangkitkan di sini
 * memakai PRNG ber-seed sehingga isinya deterministik: angka yang sama pada tiap
 * muat, jadi hasil analisis bisa dibandingkan antar sesi.
 *
 * Bentuk keluarannya sengaja sama dengan yang nanti dikembalikan
 * `GET /api/datasets/{id}/rows` — { columns: [{ name, type }], rows: [{...}] }.
 * Saat backend siap, cukup ganti isi `datasetTable()` dengan panggilan Axios;
 * seluruh engine analisis di `@/Utils` tidak perlu diubah.
 *
 * Hapus berkas ini setelah endpoint asli tersedia.
 */

function createRandom(seed) {
    let state = seed >>> 0;

    return () => {
        state = (state + 0x6d2b79f5) >>> 0;
        let t = Math.imul(state ^ (state >>> 15), 1 | state);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;

        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

function normal(random, mean, std) {
    const u = Math.max(random(), 1e-9);
    const v = random();

    return mean + std * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function pick(random, values, weights) {
    if (!weights) {
        return values[Math.floor(random() * values.length)];
    }

    const total = weights.reduce((sum, weight) => sum + weight, 0);
    let threshold = random() * total;

    for (let index = 0; index < values.length; index += 1) {
        threshold -= weights[index];

        if (threshold <= 0) {
            return values[index];
        }
    }

    return values[values.length - 1];
}

function pad(value) {
    return String(value).padStart(2, '0');
}

function stamp(startIso, minutesOffset, withTime) {
    const date = new Date(`${startIso}T00:00:00`);

    date.setMinutes(date.getMinutes() + minutesOffset);

    const day = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;

    return withTime
        ? `${day} ${pad(date.getHours())}:${pad(date.getMinutes())}`
        : day;
}

function generate(column, row, index, random) {
    if (column.kind === 'id') {
        return `${column.prefix}${column.start + index}`;
    }

    if (column.kind === 'datetime') {
        return stamp(
            column.start,
            index * column.stepMinutes,
            column.withTime ?? false,
        );
    }

    if (column.kind === 'category') {
        if (random() < (column.missingRate ?? 0)) {
            return null;
        }

        return column.derive
            ? column.derive(row, random)
            : pick(random, column.values, column.weights);
    }

    // kind === 'number'
    if (random() < (column.missingRate ?? 0)) {
        return null;
    }

    let value = column.derive
        ? column.derive(row, random)
        : normal(random, column.mean, column.std);

    // Pencilan disuntik terpisah agar rasionya terkendali — halaman anomali dan
    // rekomendasi algoritma bergantung pada proporsi ini.
    if (column.outlierRate && random() < column.outlierRate) {
        value *= column.outlierScale ?? 3.5;
    }

    if (column.min !== undefined) {
        value = Math.max(column.min, value);
    }

    if (column.max !== undefined) {
        value = Math.min(column.max, value);
    }

    const decimals = column.decimals ?? 0;

    return Number(value.toFixed(decimals));
}

const HARGA_PAKET = { 'Paket A': 400000, 'Paket B': 390000, 'Paket C': 370000 };

/*
 * Spesifikasi per dataset. `type` mengikuti kosakata yang sudah dipakai badge di
 * halaman Profiling: integer, float, category, datetime, text.
 */
const SPECS = {
    // penjualan_2026_q2.csv — transaksional: id + beberapa kolom keranjang.
    1: {
        seed: 1101,
        rowCount: 220,
        columns: [
            { name: 'id_transaksi', type: 'text', kind: 'id', prefix: 'TRX-', start: 100241 },
            { name: 'tanggal', type: 'datetime', kind: 'datetime', start: '2026-04-01', stepMinutes: 600 },
            {
                name: 'wilayah',
                type: 'category',
                kind: 'category',
                values: ['Kalimantan Timur', 'Jawa Barat', 'Jawa Timur', 'Sulawesi Selatan', 'Bali', 'Sumatera Utara'],
                weights: [26, 22, 18, 14, 11, 9],
                missingRate: 0.012,
            },
            {
                name: 'produk',
                type: 'category',
                kind: 'category',
                values: ['Paket A', 'Paket B', 'Paket C'],
                weights: [48, 33, 19],
            },
            {
                name: 'kanal',
                type: 'category',
                kind: 'category',
                values: ['Online', 'Reseller', 'Toko'],
                weights: [52, 28, 20],
            },
            {
                // Pola keranjang yang disengaja supaya association rule menemukan
                // aturan bermakna, bukan pasangan acak.
                name: 'add_on',
                type: 'category',
                kind: 'category',
                derive: (row, random) => {
                    const chance = random();

                    if (row.produk === 'Paket A') {
                        return chance < 0.66 ? 'Garansi' : chance < 0.82 ? 'Instalasi' : 'Tidak Ada';
                    }

                    if (row.produk === 'Paket B') {
                        return chance < 0.58 ? 'Instalasi' : chance < 0.79 ? 'Garansi' : 'Tidak Ada';
                    }

                    return chance < 0.52 ? 'Pelatihan' : chance < 0.7 ? 'Garansi' : 'Tidak Ada';
                },
            },
            { name: 'jumlah', type: 'integer', kind: 'number', mean: 10.4, std: 6.1, min: 1, max: 34 },
            { name: 'diskon', type: 'float', kind: 'number', mean: 0.09, std: 0.06, min: 0, max: 0.35, decimals: 2 },
            {
                name: 'pendapatan',
                type: 'float',
                kind: 'number',
                decimals: 0,
                derive: (row, random) =>
                    row.jumlah * HARGA_PAKET[row.produk] * (1 - row.diskon) +
                    normal(random, 0, 260000),
                min: 120000,
            },
            {
                name: 'biaya_iklan',
                type: 'float',
                kind: 'number',
                decimals: 0,
                missingRate: 0.087,
                derive: (row, random) =>
                    row.pendapatan * 0.24 + normal(random, 0, 180000),
                min: 40000,
            },
            { name: 'retur', type: 'integer', kind: 'number', mean: 0.4, std: 0.8, min: 0, max: 6 },
        ],
    },

    // pelanggan_segmentasi.xlsx — target kategorikal (churn), tanpa kolom waktu.
    2: {
        seed: 2202,
        rowCount: 320,
        columns: [
            { name: 'id_pelanggan', type: 'text', kind: 'id', prefix: 'CST-', start: 40001 },
            { name: 'usia', type: 'integer', kind: 'number', mean: 37, std: 11, min: 18, max: 74 },
            { name: 'tenure', type: 'integer', kind: 'number', mean: 26, std: 16, min: 1, max: 72 },
            { name: 'biaya_bulanan', type: 'float', kind: 'number', mean: 285000, std: 96000, min: 75000, decimals: 0 },
            { name: 'jumlah_komplain', type: 'integer', kind: 'number', mean: 1.4, std: 1.6, min: 0, max: 9 },
            {
                name: 'metode_bayar',
                type: 'category',
                kind: 'category',
                values: ['Transfer', 'Kartu Kredit', 'E-Wallet', 'Tunai'],
                weights: [34, 27, 24, 15],
            },
            {
                name: 'durasi_kontrak',
                type: 'category',
                kind: 'category',
                values: ['Bulanan', 'Tahunan', 'Dua Tahun'],
                weights: [46, 34, 20],
            },
            {
                name: 'kode_pos',
                type: 'category',
                kind: 'category',
                missingRate: 0.184,
                values: ['76112', '76114', '40115', '40291', '60231', '60119', '90231', '80361'],
            },
            {
                // Bergantung pada fitur di atas supaya klasifikasi benar-benar bisa
                // dipelajari — target acak akan membuat akurasi mentok di ~50%.
                name: 'churn',
                type: 'category',
                kind: 'category',
                // Bobotnya sengaja besar agar peluangnya menjauh dari 50/50:
                // target yang nyaris acak tidak bisa dipelajari model mana pun,
                // dan halaman evaluasi hanya akan menampilkan akurasi setara
                // tebakan.
                derive: (row, random) => {
                    const score =
                        row.jumlah_komplain * 1.3 +
                        (row.biaya_bulanan / 100000) * 0.5 -
                        row.tenure * 0.09 +
                        (row.durasi_kontrak === 'Bulanan'
                            ? 2.4
                            : row.durasi_kontrak === 'Tahunan'
                              ? 0.3
                              : -1.8) -
                        2.4;

                    return random() < 1 / (1 + Math.exp(-score)) ? 'Churn' : 'Bertahan';
                },
            },
        ],
    },

    // sensor_iot_juli.csv — deret waktu rapat + banyak nilai ekstrem.
    3: {
        seed: 3303,
        rowCount: 240,
        columns: [
            { name: 'id_bacaan', type: 'text', kind: 'id', prefix: 'RD-', start: 900001 },
            { name: 'waktu', type: 'datetime', kind: 'datetime', start: '2026-07-01', stepMinutes: 180, withTime: true },
            {
                name: 'perangkat',
                type: 'category',
                kind: 'category',
                values: ['SNS-01', 'SNS-02', 'SNS-03', 'SNS-04', 'SNS-05', 'SNS-06'],
            },
            { name: 'suhu', type: 'float', kind: 'number', mean: 31.2, std: 2.4, decimals: 1, outlierRate: 0.035, outlierScale: 1.9 },
            { name: 'kelembapan', type: 'float', kind: 'number', mean: 68, std: 9, min: 20, max: 100, decimals: 1 },
            { name: 'tekanan', type: 'float', kind: 'number', mean: 1009, std: 6, decimals: 1 },
            { name: 'getaran', type: 'float', kind: 'number', mean: 0.42, std: 0.18, min: 0, decimals: 2, outlierRate: 0.04, outlierScale: 4.2 },
            {
                name: 'status_perangkat',
                type: 'category',
                kind: 'category',
                derive: (row) =>
                    row.suhu > 36 || row.getaran > 1.1 ? 'Peringatan' : 'Normal',
            },
        ],
    },

    // transaksi_gagal.csv — target biner hasil retry.
    4: {
        seed: 4404,
        rowCount: 260,
        columns: [
            { name: 'id_transaksi', type: 'text', kind: 'id', prefix: 'FLT-', start: 5001 },
            { name: 'waktu', type: 'datetime', kind: 'datetime', start: '2026-07-08', stepMinutes: 240, withTime: true },
            {
                name: 'metode_bayar',
                type: 'category',
                kind: 'category',
                values: ['Transfer', 'Kartu Kredit', 'E-Wallet', 'Virtual Account'],
                weights: [30, 28, 26, 16],
            },
            {
                name: 'kode_error',
                type: 'category',
                kind: 'category',
                values: ['E-101', 'E-204', 'E-305', 'E-402', 'E-500'],
                weights: [28, 24, 20, 16, 12],
            },
            { name: 'nominal', type: 'float', kind: 'number', mean: 640000, std: 380000, min: 25000, decimals: 0, outlierRate: 0.03, outlierScale: 5 },
            { name: 'percobaan', type: 'integer', kind: 'number', mean: 2.1, std: 1.1, min: 1, max: 6 },
            { name: 'durasi_proses', type: 'float', kind: 'number', mean: 7.4, std: 3.2, min: 0.5, decimals: 1, outlierRate: 0.025, outlierScale: 4 },
            {
                name: 'berhasil_retry',
                type: 'category',
                kind: 'category',
                derive: (row, random) => {
                    const score =
                        3.2 -
                        row.percobaan * 1.6 -
                        (row.kode_error === 'E-500'
                            ? 4
                            : row.kode_error === 'E-402'
                              ? 2
                              : 0) -
                        (row.durasi_proses - 7.4) * 0.18;

                    return random() < 1 / (1 + Math.exp(-score)) ? 'Ya' : 'Tidak';
                },
            },
        ],
    },

    // inventaris_gudang.xlsx — tanpa kolom waktu, cocok untuk clustering.
    5: {
        seed: 5505,
        rowCount: 200,
        columns: [
            { name: 'sku', type: 'text', kind: 'id', prefix: 'SKU-', start: 20001 },
            {
                name: 'kategori',
                type: 'category',
                kind: 'category',
                values: ['Elektronik', 'Rumah Tangga', 'Olahraga', 'Fashion', 'Otomotif'],
                weights: [26, 24, 18, 18, 14],
            },
            {
                name: 'gudang',
                type: 'category',
                kind: 'category',
                values: ['GDG-A', 'GDG-B', 'GDG-C', 'GDG-D'],
            },
            { name: 'stok', type: 'integer', kind: 'number', mean: 140, std: 90, min: 0, max: 600 },
            { name: 'stok_minimum', type: 'integer', kind: 'number', mean: 60, std: 28, min: 5, max: 200 },
            { name: 'harga_satuan', type: 'float', kind: 'number', mean: 320000, std: 210000, min: 15000, decimals: 0 },
            {
                name: 'terjual_30hari',
                type: 'integer',
                kind: 'number',
                min: 0,
                derive: (row, random) => row.stok * 0.28 + normal(random, 12, 14),
            },
            { name: 'hari_sejak_restock', type: 'integer', kind: 'number', mean: 24, std: 16, min: 0, max: 120 },
            {
                name: 'status_stok',
                type: 'category',
                kind: 'category',
                derive: (row) => {
                    if (row.stok === 0) {
                        return 'Habis';
                    }

                    return row.stok < row.stok_minimum ? 'Menipis' : 'Aman';
                },
            },
        ],
    },

    // log_akses_aplikasi.csv — deret waktu + durasi berekor panjang.
    6: {
        seed: 6606,
        rowCount: 240,
        columns: [
            { name: 'id_log', type: 'text', kind: 'id', prefix: 'LOG-', start: 700001 },
            { name: 'waktu', type: 'datetime', kind: 'datetime', start: '2026-07-20', stepMinutes: 45, withTime: true },
            {
                name: 'endpoint',
                type: 'category',
                kind: 'category',
                values: ['/login', '/dashboard', '/datasets', '/reports', '/api/jobs'],
                weights: [24, 26, 20, 16, 14],
            },
            {
                name: 'metode',
                type: 'category',
                kind: 'category',
                values: ['GET', 'POST', 'PUT', 'DELETE'],
                weights: [58, 27, 10, 5],
            },
            {
                name: 'perangkat',
                type: 'category',
                kind: 'category',
                values: ['Desktop', 'Mobile', 'Tablet'],
                weights: [54, 36, 10],
            },
            { name: 'durasi_ms', type: 'float', kind: 'number', mean: 220, std: 95, min: 12, decimals: 0, outlierRate: 0.045, outlierScale: 6 },
            { name: 'ukuran_respons', type: 'float', kind: 'number', mean: 48, std: 26, min: 1, decimals: 1 },
            {
                name: 'status_http',
                type: 'category',
                kind: 'category',
                derive: (row, random) => {
                    if (row.durasi_ms > 900) {
                        return random() < 0.55 ? '500' : '408';
                    }

                    return pick(random, ['200', '201', '400', '401'], [72, 12, 9, 7]);
                },
            },
        ],
    },
};

/*
 * Dataset yang baru diunggah pengguna belum punya spesifikasi. Daripada halaman
 * analisis menjadi kosong, dipakai bentuk generik: satu kolom waktu, dua kolom
 * kategori, tiga kolom numerik, dan satu target biner.
 */
function fallbackSpec(id) {
    return {
        seed: 9000 + id * 7,
        rowCount: 180,
        columns: [
            { name: 'id_baris', type: 'text', kind: 'id', prefix: 'ROW-', start: 1001 },
            { name: 'tanggal', type: 'datetime', kind: 'datetime', start: '2026-06-01', stepMinutes: 720 },
            {
                name: 'kategori',
                type: 'category',
                kind: 'category',
                values: ['Kategori A', 'Kategori B', 'Kategori C', 'Kategori D'],
                weights: [34, 28, 22, 16],
            },
            {
                name: 'segmen',
                type: 'category',
                kind: 'category',
                values: ['Segmen 1', 'Segmen 2', 'Segmen 3'],
            },
            { name: 'nilai_a', type: 'float', kind: 'number', mean: 120, std: 34, min: 0, decimals: 1 },
            {
                name: 'nilai_b',
                type: 'float',
                kind: 'number',
                decimals: 1,
                min: 0,
                derive: (row, random) => row.nilai_a * 0.72 + normal(random, 18, 14),
            },
            { name: 'jumlah', type: 'integer', kind: 'number', mean: 14, std: 8, min: 0, max: 60, outlierRate: 0.02, outlierScale: 3 },
            {
                name: 'label',
                type: 'category',
                kind: 'category',
                derive: (row, random) =>
                    random() < 1 / (1 + Math.exp(-(row.nilai_b - 105) / 15))
                        ? 'Positif'
                        : 'Negatif',
            },
        ],
    };
}

function buildTable(spec) {
    const random = createRandom(spec.seed);
    const rows = [];

    for (let index = 0; index < spec.rowCount; index += 1) {
        const row = {};

        // Kolom dibangkitkan berurutan supaya `derive` bisa membaca kolom
        // sebelumnya pada baris yang sama.
        for (const column of spec.columns) {
            row[column.name] = generate(column, row, index, random);
        }

        rows.push(row);
    }

    return {
        columns: spec.columns.map(({ name, type }) => ({ name, type })),
        rows,
    };
}

const cache = new Map();

/** Tabel satu dataset: { columns: [{ name, type }], rows: [{ ... }] }. */
export function datasetTable(id) {
    const key = Number(id);

    if (!cache.has(key)) {
        cache.set(key, buildTable(SPECS[key] ?? fallbackSpec(key)));
    }

    return cache.get(key);
}
