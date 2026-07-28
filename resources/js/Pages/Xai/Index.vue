<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppBadge from '@/Components/UI/AppBadge.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useToastStore } from '@/stores/toast';
import { api } from '@/Utils/api';

/*
 * Explainable AI: menjelaskan alasan sebuah model menghasilkan prediksinya —
 * feature importance, SHAP, LIME, dan decision path (python/ml/xai.py). Metode
 * yang tidak berlaku untuk model terpilih dilaporkan beserta alasannya, bukan
 * disembunyikan.
 */
const datasetStore = useDatasetStore();
const toast = useToastStore();
const { selectedId } = storeToRefs(datasetStore);

const models = ref([]);
const modelId = ref(null);
const result = ref(null);
const isRunning = ref(false);

const explainable = computed(() => models.value.filter((model) => model.has_artifact));
const selectedModel = computed(() => models.value.find((model) => model.id === modelId.value));

async function loadModels() {
    if (!selectedId.value) {
        models.value = [];

        return;
    }

    models.value = (await api.models.list(selectedId.value)).data;

    if (!explainable.value.some((model) => model.id === modelId.value)) {
        modelId.value = explainable.value[0]?.id ?? null;
        result.value = null;
    }
}

onMounted(loadModels);
watch(selectedId, loadModels);

async function explain() {
    if (!modelId.value) {
        toast.push('Pilih model yang menyimpan artefak terlebih dahulu.', 'warning');

        return;
    }

    isRunning.value = true;

    try {
        result.value = (await api.models.explain(modelId.value)).data;
    } catch (error) {
        toast.push(error.message, 'warning');
    } finally {
        isRunning.value = false;
    }
}

const FIELD =
    'focus-ring h-9 w-full rounded-lg border-hairline bg-plane py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark';
</script>

<template>
    <PageHeader
        title="Explainable AI"
        description="Pahami alasan model menghasilkan prediksinya: feature importance, SHAP value, penjelasan LIME per baris, dan jalur keputusan."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Explainable AI' },
        ]"
    >
        <template #actions>
            <DatasetSelector />
        </template>
    </PageHeader>

    <AppCard title="Pilih Model" subtitle="Hanya model yang menyimpan artefak yang bisa dijelaskan. XAI berjalan pada sampel data, jadi butuh beberapa detik.">
        <div class="grid grid-cols-1 items-end gap-4 sm:grid-cols-3">
            <div class="sm:col-span-2">
                <label class="mb-1.5 block text-xs font-medium text-ink-2 dark:text-ink-2-dark">Model</label>
                <select v-model="modelId" :class="FIELD">
                    <option v-for="model in explainable" :key="model.id" :value="model.id">
                        {{ model.name }} — {{ model.algorithm }} (target {{ model.target }})
                    </option>
                </select>
            </div>
            <AppButton variant="primary" icon="play" :disabled="isRunning || !explainable.length" @click="explain">
                {{ isRunning ? 'Menjelaskan…' : 'Jelaskan Model' }}
            </AppButton>
        </div>
    </AppCard>

    <AppCard v-if="!explainable.length" class="mt-4" flush>
        <EmptyState
            icon="explainable-ai"
            title="Belum ada model yang bisa dijelaskan"
            description="Latih model di Machine Learning atau jalankan AutoML — artefak model pemenang otomatis tersimpan dan bisa dijelaskan di sini."
        >
            <template #action>
                <AppButton variant="primary" :to="{ name: 'automl.index' }">Jalankan AutoML</AppButton>
            </template>
        </EmptyState>
    </AppCard>

    <template v-else-if="result">
        <div class="mb-3 mt-6 flex flex-wrap items-baseline justify-between gap-2">
            <h2 class="text-sm font-semibold text-ink dark:text-ink-dark">
                Penjelasan {{ selectedModel?.name }}
            </h2>
            <p class="text-xs text-ink-3">
                {{ result.rows_explained }} baris sampel · metode tersedia: {{ result.available.join(', ') }}
            </p>
        </div>

        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChartPanel
                v-if="result.feature_importance?.length"
                title="Feature Importance"
                subtitle="Pengaruh keseluruhan tiap fitur pada model"
                type="bar"
                horizontal
                :labels="result.feature_importance.slice(0, 10).map((f) => f.feature)"
                :series="[{ label: 'Kontribusi', data: result.feature_importance.slice(0, 10).map((f) => Number(f.importance.toFixed(4))) }]"
                :height="300"
            />

            <ChartPanel
                v-if="result.shap"
                title="SHAP Value"
                :subtitle="result.shap.interpretation"
                type="bar"
                horizontal
                :labels="result.shap.contributions.slice(0, 10).map((c) => c.feature)"
                :series="[{ label: 'Rata-rata |SHAP|', data: result.shap.contributions.slice(0, 10).map((c) => Number(c.mean_abs.toFixed(5))) }]"
                :height="300"
            />

            <AppCard
                v-if="result.lime"
                :title="`LIME — baris ke-${result.lime.row + 1}`"
                :subtitle="result.lime.interpretation"
            >
                <ul class="space-y-2.5">
                    <li
                        v-for="item in result.lime.explanations"
                        :key="item.rule"
                        class="flex items-start justify-between gap-3 text-sm"
                    >
                        <span class="min-w-0 break-words font-mono text-xs text-ink dark:text-ink-dark">{{ item.rule }}</span>
                        <AppBadge :variant="item.weight >= 0 ? 'good' : 'critical'">
                            {{ item.effect }} {{ Math.abs(item.weight).toFixed(3).replace('.', ',') }}
                        </AppBadge>
                    </li>
                </ul>
            </AppCard>

            <AppCard
                v-if="result.decision_path"
                title="Decision Path"
                :subtitle="result.decision_path.interpretation"
            >
                <ol class="space-y-2">
                    <li
                        v-for="(step, index) in result.decision_path.steps"
                        :key="index"
                        class="flex items-start gap-2.5 text-sm"
                    >
                        <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-plane text-[10px] font-semibold tabular-nums text-ink-2 dark:bg-raised-dark dark:text-ink-2-dark">
                            {{ index + 1 }}
                        </span>
                        <span class="font-mono text-xs text-ink dark:text-ink-dark">{{ step.rule }}</span>
                    </li>
                </ol>
                <p class="mt-3 flex items-center gap-2 text-sm text-ink dark:text-ink-dark">
                    <AppIcon name="check" class="h-4 w-4 text-[#006300] dark:text-status-good" />
                    Kesimpulan: <span class="font-semibold">{{ result.decision_path.outcome }}</span>
                </p>
            </AppCard>
        </div>

        <AppCard
            v-if="result.unavailable?.length"
            class="mt-4"
            title="Metode yang Tidak Berlaku"
            subtitle="Tidak semua metode cocok untuk semua model — alasannya dilaporkan apa adanya."
        >
            <ul class="space-y-2">
                <li
                    v-for="item in result.unavailable"
                    :key="item.method"
                    class="flex items-start gap-2 text-sm text-ink-2 dark:text-ink-2-dark"
                >
                    <AppIcon name="warning" class="mt-0.5 h-4 w-4 shrink-0 text-[#8a5a00] dark:text-status-warning" />
                    <span><span class="font-medium text-ink dark:text-ink-dark">{{ item.method }}</span>: {{ item.reason }}</span>
                </li>
            </ul>
        </AppCard>
    </template>
</template>
