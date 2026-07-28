import { ref } from 'vue';
import { defineStore } from 'pinia';

/*
 * Notifikasi singkat (toast) lintas halaman.
 *
 * Banyak aksi (jalankan analisis, ekspor, simpan preferensi) butuh umpan balik
 * sekilas tanpa memindahkan fokus pengguna. Ditaruh di store supaya halaman mana
 * pun bisa memicu tanpa prop-drilling; penampilnya satu, ToastHost di AppLayout.
 */
let nextId = 1;

export const useToastStore = defineStore('toast', () => {
    const items = ref([]);

    /** tone: 'success' | 'info' | 'warning' */
    function push(message, tone = 'success') {
        const id = nextId++;

        items.value.push({ id, message, tone });
        setTimeout(() => dismiss(id), 4500);
    }

    function dismiss(id) {
        items.value = items.value.filter((item) => item.id !== id);
    }

    return { items, push, dismiss };
});
