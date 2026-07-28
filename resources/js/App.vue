<script setup>
import { RouterView } from 'vue-router';
import AppLayout from '@/Layouts/AppLayout.vue';

/*
 * Layout dipasang di sini, bukan di dalam tiap halaman.
 *
 * Sebelumnya setiap halaman merender <AppLayout> sendiri, sehingga berpindah
 * menu membongkar dan memasang ulang seluruh cangkang aplikasi. Akibatnya
 * posisi gulir sidebar kembali ke atas dan lebar sidebar yang sedang dipilih
 * ikut ter-reset setiap kali navigasi.
 *
 * Dengan layout di luar RouterView, sidebar hanya dipasang sekali dan
 * keadaannya bertahan; yang berganti hanya isi halamannya.
 */
</script>

<template>
    <AppLayout>
        <RouterView />
    </AppLayout>
</template>
