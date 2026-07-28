import { ref } from 'vue';
import { defineStore } from 'pinia';

/*
 * Dialog konfirmasi lintas halaman.
 *
 * Pengganti `window.confirm()` bawaan peramban agar tampilannya konsisten
 * dengan antarmuka aplikasi. `open()` mengembalikan Promise<boolean> sehingga
 * pemanggil cukup `await` — penampilnya satu, ConfirmDialog di AppLayout.
 */
let resolver = null;

export const useConfirmStore = defineStore('confirm', () => {
    const isOpen = ref(false);
    const options = ref({
        title: '',
        message: '',
        confirmLabel: 'Hapus',
        tone: 'danger',
    });

    function open(payload) {
        options.value = {
            confirmLabel: 'Hapus',
            tone: 'danger',
            ...payload,
        };
        isOpen.value = true;

        return new Promise((resolve) => {
            resolver = resolve;
        });
    }

    function close(result) {
        isOpen.value = false;
        resolver?.(result);
        resolver = null;
    }

    return { isOpen, options, open, close };
});
