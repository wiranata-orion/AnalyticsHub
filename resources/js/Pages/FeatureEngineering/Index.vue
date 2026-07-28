<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import DataTable from '@/Components/UI/DataTable.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useToastStore } from '@/stores/toast';
import { useConfirmStore } from '@/stores/confirm';
import { api } from '@/Utils/api';

/*
 * Feature Engineering: susun langkah transformasi (encoding, scaling, PCA),
 * jalankan di engine Python, dan hasilnya tersimpan sebagai feature set yang
 * bisa langsung dipilih saat melatih model di Machine Learning / AutoML.
 */
const datasetStore = useDatasetStore();
const toast = useToastStore();
const confirm = useConfirmStore();
const { selectedId } = storeToRefs(datasetStore);

const STEPS = [
    { value: 'label_encoding', label: 'Label Encoding', hint: 'Kategori menjadi angka urut.' },
    { value: 'one_hot', label: 'One-Hot Encoding', hint: 'Satu kolom biner per kategori.' },
    { value: 'standard_scaling', label: 'Standard Scaling', hint: 'Rata-rata 0, simpangan 1.' },
    { value: 'minmax_scaling', label: 'Min-Max Scaling', hint: 'Rentang 0 sampai 1.' },
    { value: 'normalization', label: 'Normalization', hint: 'Panjang vektor baris = 1.' },
    { value: 'pca', label: 'PCA', hint: 'Reduksi dimensi ke komponen utama.' },
];

const chosen = ref([]);
const name = ref('');
const target = ref('');
const pcaComponents = ref(3);
const isRunning = ref(false);
const sets = ref([]);
const selection = ref(null);
const isSelecting = ref(false);

const targetOptions = computed(() =>
    datasetStore.columns.filter(
        (c) => !c.is_identifier && c.type !== 'datetime' && (['integer', 'float'].includes(c.type) || c.unique <= 20),
    ),
);

function toggle(step) {
    chosen.value = chosen.value.includes(step)
        ? chosen.value.filter((item) => item !== step)
        : [...chosen.value, step];
}

async function loadSets() {
    if (!selectedId.value) {
        sets.value = [];

        return;
    }

    try {
        sets.value = (await api.features.list(selectedId.value)).data;
    } catch {
        sets.value = [];
    }
}

onMounted(loadSets);
watch(selectedId, () => {
    loadSets();
    selection.value = null;
    target.value = '';
});

async function transform() {
    if (!chosen.value.length) {
        toast.push('Pilih minimal satu langkah transformasi.', 'warning');

        return;
    }

    isRunning.value = true;

    try {
        const steps = chosen.value.map((step) =>
            step === 'pca' ? { step, components: Number(pcaComponents.value) } : { step },
        );

        await api.features.create(selectedId.value, {
            name: name.value || undefined,
            target: target.value || undefined,
            steps,
        });

        toast.push('Feature set dibuat dan siap dipakai di Machine Learning.');
        name.value = '';
        await loadSets();
    } catch (error) {
        toast.push(error.message, 'warning');
    } finally {
        isRunning.value = false;
    }
}

async function removeSet(set) {
    const approved = await confirm.open({
        title: 'Hapus feature set',
        message: `"${set.name}" akan dihapus. Model yang sudah dilatih darinya tetap tersimpan.`,
    });

    if (!approved) {
        return;
    }

    await api.features.remove(set.id);
    toast.push('Feature set dihapus.');
    await loadSets();
}

async function runSelection() {
    if (!target.value) {
        toast.push('Pilih kolom target untuk feature selection.', 'warning');

        return;
    }

    isSelecting.value = true;

    try {
        selection.value = (await api.features.selection(selectedId.value, target.value)).data;
    } catch (error) {
        toast.push(error.message, 'warning');
    } finally {
        isSelecting.value = false;
    }
}

const FIELD =
    'focus-ring h-9 w-full rounded-lg border-hairline bg-plane py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark';
</script>

<template>
    <PageHeader
        title="Feature Engineering"
        description="Encoding, scaling, PCA, dan feature selection. Hasilnya tersimpan sebagai feature set yang dapat langsung dipakai melatih model."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Feature Engineering' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
        </template>
    </PageHeader>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div class="lg:col-span-2">
            <AppCard
                title="Transformasi Baru"
                subtitle="Langkah dijalankan berurutan sesuai pilihan. Kolom target dikecualikan dari transformasi."
            >
                <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <button
                        v-for="step in STEPS"
                        :key="step.value"
                        type="button"
                        class="focus-ring flex items-start gap-3 rounded-xl border p-4 text-left transition-colors"
                        :class="chosen.includes(step.value)
                            ? 'border-accent ring-1 ring-accent dark:border-accent-dark dark:ring-accent-dark'
                            : 'border-hairline hover:bg-plane dark:border-hairline-dark dark:hover:bg-raised-dark/60'"
                        :aria-pressed="chosen.includes(step.value)"
                        @click="toggle(step.value)"
                    >
                        <AppIcon
                            :name="chosen.includes(step.value) ? 'check' : 'feature-engineering'"
                            class="mt-0.5 h-4 w-4 shrink-0"
                            :class="chosen.includes(step.value) ? 'text-accent dark:text-accent-dark' : 'text-ink-3'"
                        />
                        <span>
                            <span class="block text-sm font-medium text-ink dark:text-ink-dark">{{ step.label }}</span>
                            <span class="mt-0.5 block text-xs text-ink-2 dark:text-ink-2-dark">{{ step.hint }}</span>
                        </span>
                    </button>
                </div>

                <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <div>
                        <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Nama (opsional)</label>
                        <input
                            v-model="name"
                            type="text"
                            placeholder="Mengikuti waktu dibuat"
                            class="focus-ring h-9 w-full rounded-lg border-hairline bg-plane px-3 text-sm text-ink placeholder:text-ink-3 focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                        />
                    </div>
                    <div>
                        <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Kolom Target (dilindungi)</label>
                        <select v-model="target" :class="FIELD">
                            <option value="">Tanpa target</option>
                            <option v-for="c in targetOptions" :key="c.name" :value="c.name">{{ c.name }}</option>
                        </select>
                    </div>
                    <div v-if="chosen.includes('pca')">
                        <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Komponen PCA</label>
                        <input v-model.number="pcaComponents" type="number" min="1" max="20" :class="FIELD" />
                    </div>
                </div>

                <template #footer>
                    <div class="flex items-center justify-between gap-3">
                        <p class="text-xs text-ink-3">{{ chosen.length }} langkah dipilih · dataset asli tidak diubah.</p>
                        <AppButton variant="primary" icon="play" :disabled="isRunning" @click="transform">
                            {{ isRunning ? 'Memproses…' : 'Jalankan Transformasi' }}
                        </AppButton>
                    </div>
                </template>
            </AppCard>

            <AppCard class="mt-4" title="Feature Set Tersimpan" subtitle="Pilih salah satunya sebagai sumber data saat melatih model." flush>
                <DataTable
                    v-if="sets.length"
                    :columns="[
                        { key: 'name', label: 'Nama' },
                        { key: 'steps', label: 'Langkah', wrap: true },
                        { key: 'row_count', label: 'Baris', align: 'right', numeric: true },
                        { key: 'column_count', label: 'Kolom', align: 'right', numeric: true },
                        { key: 'created_at', label: 'Dibuat', align: 'right' },
                        { key: 'actions', label: '', align: 'right', width: '1%' },
                    ]"
                    :rows="sets"
                >
                    <template #cell-name="{ row }">
                        <span class="font-medium text-ink dark:text-ink-dark">{{ row.name }}</span>
                    </template>
                    <template #cell-steps="{ row }">
                        <span class="flex flex-wrap gap-1">
                            <AppBadge v-for="step in row.steps" :key="step.step">{{ step.step }}</AppBadge>
                        </span>
                    </template>
                    <template #cell-actions="{ row }">
                        <button
                            type="button"
                            class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-status-critical"
                            title="Hapus feature set"
                            @click="removeSet(row)"
                        >
                            <AppIcon name="trash" class="h-4 w-4" />
                            <span class="sr-only">Hapus {{ row.name }}</span>
                        </button>
                    </template>
                </DataTable>
                <EmptyState
                    v-else
                    icon="feature-engineering"
                    title="Belum ada feature set"
                    description="Jalankan transformasi di atas untuk membuat versi dataset yang siap dilatih."
                />
            </AppCard>
        </div>

        <AppCard title="Feature Selection" subtitle="Peringkat kolom menurut kekuatannya terhadap target — uji univariat dan Random Forest sekaligus.">
            <div class="space-y-4">
                <div>
                    <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Kolom Target</label>
                    <select v-model="target" :class="FIELD">
                        <option value="">Pilih target…</option>
                        <option v-for="c in targetOptions" :key="c.name" :value="c.name">{{ c.name }} ({{ c.type }})</option>
                    </select>
                </div>
                <AppButton variant="primary" icon="play" :disabled="isSelecting" @click="runSelection">
                    {{ isSelecting ? 'Menilai…' : 'Nilai Fitur' }}
                </AppButton>

                <template v-if="selection">
                    <p class="text-xs text-ink-2 dark:text-ink-2-dark">{{ selection.interpretation }}</p>
                    <ul class="space-y-2">
                        <li
                            v-for="feature in selection.features.slice(0, 12)"
                            :key="feature.feature"
                            class="flex items-center justify-between gap-2 text-sm"
                        >
                            <span class="flex min-w-0 items-center gap-1.5">
                                <AppIcon
                                    v-if="selection.recommended.includes(feature.feature)"
                                    name="check"
                                    class="h-3.5 w-3.5 shrink-0 text-[#006300] dark:text-status-good"
                                />
                                <span class="truncate text-ink dark:text-ink-dark">{{ feature.feature }}</span>
                            </span>
                            <span class="shrink-0 tabular-nums text-ink-3">
                                {{ (feature.importance * 100).toFixed(1).replace('.', ',') }}%
                            </span>
                        </li>
                    </ul>
                </template>
            </div>
        </AppCard>
    </div>
</template>
