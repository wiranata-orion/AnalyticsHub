<script setup>
/*
 * Tabel generik. Kolom diberikan sebagai
 * { key, label, align?: 'left'|'right', numeric?: boolean, width?: string }.
 *
 * Sel dapat di-override lewat slot bernama `cell-<key>`, sehingga badge, tautan,
 * atau tombol aksi tidak perlu logika kondisional di dalam komponen ini.
 *
 * Pembungkusnya selalu `overflow-x-auto` supaya tabel lebar menggulir di dalam
 * kartunya sendiri, bukan membuat seluruh halaman menggulir horizontal.
 */
defineProps({
    columns: {
        type: Array,
        required: true,
    },
    rows: {
        type: Array,
        required: true,
    },
    rowKey: {
        type: String,
        default: 'id',
    },
});
</script>

<template>
    <div class="overflow-x-auto">
        <table class="w-full min-w-full border-collapse text-sm">
            <thead>
                <tr class="border-b border-hairline dark:border-hairline-dark">
                    <th
                        v-for="column in columns"
                        :key="column.key"
                        scope="col"
                        class="whitespace-nowrap px-5 py-2.5 text-xs font-medium uppercase tracking-wide text-ink-3"
                        :class="column.align === 'right' ? 'text-right' : 'text-left'"
                        :style="column.width ? { width: column.width } : null"
                    >
                        {{ column.label }}
                    </th>
                </tr>
            </thead>

            <tbody>
                <tr
                    v-for="row in rows"
                    :key="row[rowKey]"
                    class="border-b border-hairline last:border-0 transition-colors hover:bg-plane dark:border-hairline-dark dark:hover:bg-raised-dark/60"
                >
                    <td
                        v-for="column in columns"
                        :key="column.key"
                        class="whitespace-nowrap px-5 py-3 text-ink-2 dark:text-ink-2-dark"
                        :class="[
                            column.align === 'right' ? 'text-right' : 'text-left',
                            column.numeric ? 'tabular-nums' : '',
                        ]"
                    >
                        <slot :name="`cell-${column.key}`" :row="row">
                            {{ row[column.key] }}
                        </slot>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>
