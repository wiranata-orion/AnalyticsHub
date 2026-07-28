<script setup>
import { computed, ref } from 'vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import { emptyConfig } from '@/Utils/autoVisualization';
import {
    AGGREGATIONS,
    CHART_TYPES,
    MULTI_COLUMN_TYPES,
    TIME_GRAINS,
} from '@/Utils/chartBuilder';
import { isNumericType } from '@/Utils/profiler';

/*
 * Formulir satu grafik, dipakai untuk membuat maupun mengubah.
 *
 * Dipisah dari halaman karena dipasang di dua tempat: di bawah header saat
 * membuat grafik baru, dan tepat di bawah panel yang sedang diubah — sehingga
 * pengguna tidak perlu menggulir ke atas untuk menyunting grafik yang jauh di
 * bawah.
 *
 * Konfigurasinya disalin ke draf lokal dan baru dikirim lewat `save`, jadi
 * menutup formulir tidak meninggalkan panel dalam keadaan setengah berubah.
 * Pemanggil memasang `key` per grafik agar draf tersegar saat berpindah panel.
 */
const props = defineProps({
    profile: {
        type: Object,
        required: true,
    },
    // Konfigurasi awal; dibiarkan kosong berarti grafik baru.
    config: {
        type: Object,
        default: () => ({}),
    },
    isNew: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(['save', 'cancel']);

const draft = ref({ ...emptyConfig(), ...props.config });

const analyzable = computed(() =>
    props.profile.columns.filter((column) => !column.isIdentifier),
);

const numericColumns = computed(() =>
    analyzable.value.filter((column) => isNumericType(column.type)),
);

const groupableColumns = computed(() =>
    analyzable.value.filter(
        (column) => column.type === 'category' && column.unique <= 12,
    ),
);

const isMultiColumn = computed(() =>
    MULTI_COLUMN_TYPES.includes(draft.value.type),
);

const xMeta = computed(() =>
    props.profile.columns.find((column) => column.name === draft.value.xColumn),
);

const filterValues = computed(() => {
    const column = props.profile.columns.find(
        (item) => item.name === draft.value.filterColumn,
    );

    return column?.top?.slice(0, 20) ?? [];
});

function toggleColumn(name) {
    draft.value.columns = draft.value.columns.includes(name)
        ? draft.value.columns.filter((item) => item !== name)
        : [...draft.value.columns, name];
}

const FIELD_CLASS =
    'focus-ring h-9 w-full rounded-lg border-hairline bg-plane py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark';
const LABEL_CLASS =
    'mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark';
</script>

<template>
    <AppCard
        :title="isNew ? 'Grafik Baru' : 'Ubah Grafik'"
        :subtitle="`Dihitung dari ${profile.rowCount.toLocaleString('id-ID')} baris dataset terpilih.`"
    >
        <form
            class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
            @submit.prevent="emit('save', { ...draft })"
        >
            <div>
                <label for="chart-title" :class="LABEL_CLASS">
                    Judul (opsional)
                </label>
                <input
                    id="chart-title"
                    v-model="draft.title"
                    type="text"
                    placeholder="Mengikuti kolom yang dipilih"
                    class="focus-ring h-9 w-full rounded-lg border-hairline bg-plane px-3 text-sm text-ink placeholder:text-ink-3 focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                />
            </div>

            <div>
                <label for="chart-type" :class="LABEL_CLASS">Jenis Grafik</label>
                <select id="chart-type" v-model="draft.type" :class="FIELD_CLASS">
                    <option
                        v-for="type in CHART_TYPES"
                        :key="type.value"
                        :value="type.value"
                    >
                        {{ type.label }}
                    </option>
                </select>
            </div>

            <template v-if="!isMultiColumn">
                <div>
                    <label for="chart-x" :class="LABEL_CLASS">Sumbu X</label>
                    <select id="chart-x" v-model="draft.xColumn" :class="FIELD_CLASS">
                        <option
                            v-for="column in analyzable"
                            :key="column.name"
                            :value="column.name"
                        >
                            {{ column.name }} ({{ column.type }})
                        </option>
                    </select>
                </div>

                <div>
                    <label for="chart-y" :class="LABEL_CLASS">Sumbu Y</label>
                    <select
                        id="chart-y"
                        v-model="draft.yColumn"
                        :disabled="draft.aggregation === 'count' && draft.type !== 'scatter'"
                        :class="[FIELD_CLASS, 'disabled:opacity-50']"
                    >
                        <option
                            v-for="column in numericColumns"
                            :key="column.name"
                            :value="column.name"
                        >
                            {{ column.name }}
                        </option>
                    </select>
                </div>

                <div v-if="draft.type !== 'scatter'">
                    <label for="chart-aggregation" :class="LABEL_CLASS">
                        Agregasi
                    </label>
                    <select
                        id="chart-aggregation"
                        v-model="draft.aggregation"
                        :class="FIELD_CLASS"
                    >
                        <option
                            v-for="item in AGGREGATIONS"
                            :key="item.value"
                            :value="item.value"
                        >
                            {{ item.label }}
                        </option>
                    </select>
                </div>

                <div>
                    <label for="chart-color" :class="LABEL_CLASS">
                        Warna (opsional)
                    </label>
                    <select
                        id="chart-color"
                        v-model="draft.colorColumn"
                        :class="FIELD_CLASS"
                    >
                        <option value="">Satu warna</option>
                        <option
                            v-for="column in groupableColumns"
                            :key="column.name"
                            :value="column.name"
                        >
                            Pisah per {{ column.name }}
                        </option>
                    </select>
                </div>

                <div>
                    <label for="chart-filter" :class="LABEL_CLASS">
                        Filter (opsional)
                    </label>
                    <select
                        id="chart-filter"
                        v-model="draft.filterColumn"
                        :class="FIELD_CLASS"
                        @change="draft.filterValue = ''"
                    >
                        <option value="">Tanpa filter</option>
                        <option
                            v-for="column in groupableColumns"
                            :key="column.name"
                            :value="column.name"
                        >
                            {{ column.name }}
                        </option>
                    </select>
                </div>

                <div v-if="draft.filterColumn">
                    <label for="chart-filter-value" :class="LABEL_CLASS">
                        Nilai Filter
                    </label>
                    <select
                        id="chart-filter-value"
                        v-model="draft.filterValue"
                        :class="FIELD_CLASS"
                    >
                        <option value="">Pilih nilai…</option>
                        <option
                            v-for="item in filterValues"
                            :key="item.value"
                            :value="item.value"
                        >
                            {{ item.value }} ({{ item.count }} baris)
                        </option>
                    </select>
                </div>

                <div v-if="xMeta?.type === 'datetime'">
                    <label for="chart-grain" :class="LABEL_CLASS">
                        Satuan Waktu
                    </label>
                    <select
                        id="chart-grain"
                        v-model="draft.timeGrain"
                        :class="FIELD_CLASS"
                    >
                        <option
                            v-for="grain in TIME_GRAINS"
                            :key="grain.value"
                            :value="grain.value"
                        >
                            {{ grain.label }}
                        </option>
                    </select>
                </div>

                <label
                    v-if="['line', 'area'].includes(draft.type) && !draft.colorColumn"
                    class="flex items-center gap-2.5 sm:col-span-2 lg:col-span-3"
                >
                    <input
                        v-model="draft.smooth"
                        type="checkbox"
                        class="focus-ring h-4 w-4 rounded border-hairline text-accent focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark"
                    />
                    <span class="text-sm text-ink-2 dark:text-ink-2-dark">
                        Tambahkan garis rata-rata bergerak
                    </span>
                </label>
            </template>

            <div v-else class="sm:col-span-2 lg:col-span-3">
                <p class="mb-2 text-xs font-medium text-ink-2 dark:text-ink-2-dark">
                    Kolom numerik ({{ draft.columns.length }} dipilih)
                </p>

                <div class="flex flex-wrap gap-2">
                    <button
                        v-for="column in numericColumns"
                        :key="column.name"
                        type="button"
                        class="focus-ring rounded-lg px-3 py-1.5 text-xs font-medium ring-1 ring-inset transition-colors"
                        :class="
                            draft.columns.includes(column.name)
                                ? 'bg-accent text-white ring-accent dark:bg-accent-dark dark:ring-accent-dark'
                                : 'text-ink-2 ring-hairline hover:bg-plane dark:text-ink-2-dark dark:ring-hairline-dark dark:hover:bg-raised-dark'
                        "
                        :aria-pressed="draft.columns.includes(column.name)"
                        @click="toggleColumn(column.name)"
                    >
                        {{ column.name }}
                    </button>
                </div>
            </div>
        </form>

        <template #footer>
            <div class="flex items-center justify-end gap-2">
                <AppButton @click="emit('cancel')">Batal</AppButton>
                <AppButton
                    variant="primary"
                    icon="check"
                    @click="emit('save', { ...draft })"
                >
                    {{ isNew ? 'Tambahkan' : 'Simpan Perubahan' }}
                </AppButton>
            </div>
        </template>
    </AppCard>
</template>
