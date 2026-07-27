<script setup>
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { visualization } from '@/data/placeholder';

const { revenueByRegion, monthlyTrend, distribution, scatter, composition } =
    visualization;
</script>

<template>
    <AppLayout>
        <PageHeader
            title="Visualisasi"
            description="Grafik yang dihasilkan dari dataset terpilih. Setiap panel dapat dibaca sebagai tabel."
            :breadcrumbs="[
                { label: 'Dashboard', to: { name: 'dashboard' } },
                { label: 'Visualisasi' },
            ]"
        >
            <template #actions>
                <DatasetSelector />
                <AppButton variant="primary" icon="plus">Buat Grafik</AppButton>
            </template>
        </PageHeader>

        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <!-- Perbandingan besaran antar kategori -> batang horizontal,
                 supaya nama wilayah terbaca tanpa dimiringkan. -->
            <ChartPanel
                title="Pendapatan per Wilayah"
                subtitle="Dalam juta rupiah"
                type="bar"
                horizontal
                :labels="revenueByRegion.labels"
                :series="revenueByRegion.series"
                :height="280"
            />

            <!-- Perubahan sepanjang waktu -> garis. -->
            <ChartPanel
                title="Tren Penjualan Bulanan"
                subtitle="Per lini produk"
                type="line"
                :labels="monthlyTrend.labels"
                :series="monthlyTrend.series"
                :height="280"
            />

            <!-- Sebaran satu variabel -> histogram (batang tanpa jeda kategori). -->
            <ChartPanel
                title="Distribusi Jumlah Pembelian"
                subtitle="Frekuensi per rentang nilai"
                type="bar"
                :labels="distribution.labels"
                :series="distribution.series"
                :height="280"
            />

            <!-- Hubungan dua variabel -> scatter. Maksimal tiga seri:
                 pada scatter semua pasangan warna tampil berdampingan. -->
            <ChartPanel
                title="Biaya Iklan vs Pendapatan"
                subtitle="Setiap titik mewakili satu transaksi"
                type="scatter"
                :series="scatter.series"
                :height="280"
            />

            <ChartPanel
                title="Komposisi Produk"
                subtitle="Pangsa terhadap total penjualan"
                type="doughnut"
                :labels="composition.labels"
                :series="composition.series"
                value-suffix="%"
                :height="280"
            />

            <ChartPanel
                title="Tren Kumulatif"
                subtitle="Akumulasi penjualan seluruh produk"
                type="area"
                :labels="monthlyTrend.labels"
                :series="[monthlyTrend.series[0]]"
                :height="280"
            />
        </div>
    </AppLayout>
</template>
