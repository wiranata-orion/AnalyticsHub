<script setup>
import { storeToRefs } from 'pinia';
import { useDatasetStore } from '@/stores/dataset';
import AppIcon from '@/Components/UI/AppIcon.vue';

/*
 * Pemilih dataset aktif, dipakai halaman profiling, cleaning, visualisasi,
 * mining, dan machine learning.
 *
 * Nilainya diambil dari store, bukan prop, supaya pilihan pengguna terbawa saat
 * berpindah menu — tanpa itu dataset harus dipilih ulang di setiap halaman.
 */
const store = useDatasetStore();
const { items, selectedId } = storeToRefs(store);
</script>

<template>
    <div class="flex items-center gap-2">
        <label
            for="dataset-selector"
            class="shrink-0 text-xs font-medium text-ink-3"
        >
            Dataset
        </label>

        <div class="relative">
            <AppIcon
                name="datasets"
                class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3"
            />
            <!-- Lewat store.select(), bukan v-model: pemilihan juga harus memuat
                 detail kolom dataset dari API, bukan sekadar mengganti id. -->
            <select
                id="dataset-selector"
                :value="selectedId ?? ''"
                class="focus-ring h-9 min-w-[15rem] rounded-lg border-hairline bg-surface py-0 pl-9 pr-8 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-surface-dark dark:text-ink-dark"
                @change="store.select($event.target.value)"
            >
                <option
                    v-for="dataset in items"
                    :key="dataset.id"
                    :value="dataset.id"
                >
                    {{ dataset.name }}
                </option>
            </select>
        </div>
    </div>
</template>
