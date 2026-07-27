import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';

/*
 * Frontend berdiri sendiri: Vite yang menyajikan `index.html`, sehingga
 * `npm run dev` sudah cukup untuk melihat antarmuka tanpa menjalankan PHP.
 *
 * Laravel nanti hanya menyediakan REST API yang dikonsumsi lewat Axios, jadi
 * `laravel-vite-plugin` tidak dipakai lagi.
 */
export default defineConfig({
    plugins: [vue()],

    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./resources/js', import.meta.url)),
        },
    },

    server: {
        // Dipaksa IPv4: sebagian peramban di Windows gagal memuat modul dari
        // alamat IPv6 (`[::1]`) yang jadi default Vite.
        host: '127.0.0.1',
        port: 5173,
        open: true,
    },

    build: {
        outDir: 'dist',
        emptyOutDir: true,
    },
});
