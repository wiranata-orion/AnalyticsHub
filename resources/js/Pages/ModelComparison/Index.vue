<script setup>
import { onMounted, ref, watch } from 'vue';
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
import { asDecimal, asPercent } from '@/Utils/ml/metrics';

/*
 * Model Comparison: seluruh model tersimpan untuk dataset terpilih dalam satu
 * tabel — akurasi/presisi/recall/F1 (atau R²/RMSE), waktu latih, dan waktu
 * prediksi — supaya pemilihan model terbaik bisa mempertimbangkan kecepatan,
 * bukan hanya skor.
 */
const datasetStore = useDatasetStore();
const toast = useToastStore();
const confirm = useConfirmStore();
const { selectedId } = storeToRefs(datasetStore);

const models = ref([]);
const isLoading = ref(false);

async function load() {
    if (!selectedId.value) {
        models.value = [];

        return;
    }

    isLoading.value = true;

    try {
        models.value = (await api.models.list(selectedId.value)).data;
    } catch (error) {
        toast.push(error.message, 'warning');
    } finally {
        isLoading.value = false;
    }
}

onMounted(load);
watch(selectedId, load);

async function removeModel(model) {
    const approved = await confirm.open({
        title: 'Hapus model',
        message: `Model "${model.name}" akan dihapus beserta artefaknya.`,
    });

    if (!approved) {
        return;
    }

    await api.models.remove(model.id);
    toast.push(`Model "${model.name}" dihapus.`);
    await load();
}

const metric = (row, key) => row.metrics?.[key];

/*
 * Kolom dijaga tetap sedikit supaya tabel muat tanpa digeser ke samping:
 * nama dan target boleh membungkus, dan waktu latih/prediksi digabung dalam
 * satu kolom karena keduanya selalu dibaca berpasangan.
 */
const COLUMNS = [
    { key: 'name', label: 'Model', wrap: true },
    { key: 'task', label: 'Tugas' },
    { key: 'target', label: 'Target', wrap: true },
    { key: 'accuracy', label: 'Skor', align: 'right', numeric: true },
    { key: 'precision', label: 'Presisi', align: 'right', numeric: true },
    { key: 'recall', label: 'Recall', align: 'right', numeric: true },
    { key: 'f1', label: 'F1', align: 'right', numeric: true },
    { key: 'timing', label: 'Latih / Prediksi', align: 'right', numeric: true },
    { key: 'actions', label: '', align: 'right', width: '1%' },
];
</script>

<template>
    <PageHeader
        title="Model Comparison"
        description="Bandingkan seluruh model yang pernah dilatih pada dataset ini — skor, waktu latih, dan waktu prediksi berdampingan."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Model Comparison' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
            <AppButton icon="refresh" :disabled="isLoading" @click="load">Muat Ulang</AppButton>
        </template>
    </PageHeader>

    <AppCard v-if="!models.length && !isLoading" flush>
        <EmptyState
            icon="model-comparison"
            title="Belum ada model untuk dataset ini"
            description="Latih model di Machine Learning, atau jalankan AutoML untuk mengisi tabel perbandingan sekaligus."
        >
            <template #action>
                <div class="flex flex-wrap justify-center gap-2">
                    <AppButton :to="{ name: 'machine-learning.index' }">Machine Learning</AppButton>
                    <AppButton variant="primary" :to="{ name: 'automl.index' }">Jalankan AutoML</AppButton>
                </div>
            </template>
        </EmptyState>
    </AppCard>

    <AppCard
        v-else-if="models.length"
        title="Perbandingan Model"
        :subtitle="`${models.length} model · model bertanda Terbaik adalah pemenang AutoML terakhir`"
        flush
    >
        <DataTable :columns="COLUMNS" :rows="models">
            <template #cell-name="{ row }">
                <span class="flex items-center gap-2">
                    <span class="font-medium text-ink dark:text-ink-dark">{{ row.name }}</span>
                    <AppBadge v-if="row.is_best" variant="good">Terbaik</AppBadge>
                    <AppBadge v-if="row.has_artifact" variant="info">Artefak</AppBadge>
                </span>
            </template>
            <template #cell-task="{ row }">
                {{ row.task === 'classification' ? 'Klasifikasi' : 'Regresi' }}
            </template>
            <template #cell-accuracy="{ row }">
                <span class="font-medium text-ink dark:text-ink-dark">
                    {{ row.task === 'classification'
                        ? (metric(row, 'accuracy') != null ? asPercent(metric(row, 'accuracy')) : '—')
                        : (metric(row, 'r2') != null ? asDecimal(metric(row, 'r2')) : '—') }}
                </span>
            </template>
            <template #cell-precision="{ row }">
                {{ metric(row, 'precision') != null ? asPercent(metric(row, 'precision')) : '—' }}
            </template>
            <template #cell-recall="{ row }">
                {{ metric(row, 'recall') != null ? asPercent(metric(row, 'recall')) : '—' }}
            </template>
            <template #cell-f1="{ row }">
                {{ metric(row, 'f1') != null ? asPercent(metric(row, 'f1'))
                    : metric(row, 'rmse') != null ? `RMSE ${Math.round(metric(row, 'rmse')).toLocaleString('id-ID')}` : '—' }}
            </template>
            <template #cell-timing="{ row }">
                {{ row.training_time_ms != null ? `${row.training_time_ms} ms` : '—' }}
                <span class="text-ink-3"> / </span>
                {{ row.prediction_time_ms != null ? `${row.prediction_time_ms} ms` : '—' }}
            </template>
            <template #cell-actions="{ row }">
                <button
                    type="button"
                    class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-status-critical"
                    title="Hapus model"
                    @click="removeModel(row)"
                >
                    <AppIcon name="trash" class="h-4 w-4" />
                    <span class="sr-only">Hapus {{ row.name }}</span>
                </button>
            </template>
        </DataTable>
    </AppCard>
</template>
