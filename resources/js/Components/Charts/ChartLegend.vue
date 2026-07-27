<script setup>
/*
 * Legend selalu tampil untuk >= 2 seri, sehingga identitas tidak pernah dibawa
 * warna saja. Untuk seri tunggal, judul panel sudah menamai datanya — pemanggil
 * yang menyembunyikannya.
 */
defineProps({
    // { label, color, value? }
    entries: {
        type: Array,
        required: true,
    },
});
</script>

<template>
    <ul class="flex flex-wrap items-center gap-x-4 gap-y-1.5">
        <li
            v-for="entry in entries"
            :key="entry.label"
            class="flex items-center gap-1.5 text-xs"
        >
            <span
                class="h-2 w-2 shrink-0 rounded-full"
                :style="{ backgroundColor: entry.color }"
                aria-hidden="true"
            />
            <span class="text-ink-2 dark:text-ink-2-dark">{{ entry.label }}</span>
            <span
                v-if="entry.value !== undefined"
                class="font-medium tabular-nums text-ink dark:text-ink-dark"
            >
                {{ entry.value }}
            </span>
        </li>
    </ul>
</template>
