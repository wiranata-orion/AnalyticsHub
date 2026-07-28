<script setup>
import { computed, ref, watch } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import EmptyState from '@/Components/UI/EmptyState.vue';
import ChartPanel from '@/Components/Charts/ChartPanel.vue';
import ChartEditor from '@/Components/Charts/ChartEditor.vue';
import BoxPlot from '@/Components/Charts/BoxPlot.vue';
import CorrelationHeatmap from '@/Components/Charts/CorrelationHeatmap.vue';
import DatasetSelector from '@/Components/Datasets/DatasetSelector.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useToastStore } from '@/stores/toast';
import { useVisualizationStore } from '@/stores/visualization';
import { datasetAnalysis } from '@/Utils/analysis';
import { autoChartConfigs, emptyConfig } from '@/Utils/autoVisualization';
import { buildChart } from '@/Utils/chartBuilder';
import { isNumericType } from '@/Utils/profiler';

/*
 * Satu daftar grafik untuk satu dataset.
 *
 * Panel awalnya dipilihkan sistem dari hasil profiling (lihat
 * `@/Utils/autoVisualization`), tetapi bentuk konfigurasinya sama dengan yang
 * dihasilkan formulir. Karena itu setiap panel — termasuk yang muncul otomatis —
 * bisa langsung dibuka dan diubah, dan tidak perlu ada daftar grafik kedua yang
 * terpisah.
 *
 * Susunannya disimpan di store per dataset, sehingga hasil penyuntingan tetap
 * ada saat pengguna berpindah menu lalu kembali.
 */
const datasetStore = useDatasetStore();
const visualizationStore = useVisualizationStore();
const toast = useToastStore();

const analysis = computed(() => datasetAnalysis(datasetStore.selectedId));
const profile = computed(() => analysis.value.profile);

const charts = computed(() =>
    visualizationStore.charts(datasetStore.selectedId).map((chart) => ({
        id: chart.id,
        config: chart.config,
        built: buildChart(analysis.value.table, profile.value, chart.config),
    })),
);

/*
 * Formulir muncul di dua tempat: di bawah header saat membuat grafik baru, dan
 * tepat di bawah panel yang sedang diubah. Yang kedua itu yang penting — daftar
 * grafik bisa panjang, dan menaruh formulir hanya di atas memaksa pengguna
 * menggulir bolak-balik untuk melihat hasil suntingannya.
 */
const editorOpen = ref(false);
const editingId = ref(null);
const editorSeed = ref(emptyConfig());

function startCreate() {
    const numeric = profile.value.columns.filter(
        (column) => !column.isIdentifier && isNumericType(column.type),
    );
    const groupable = profile.value.columns.filter(
        (column) => !column.isIdentifier && column.type === 'category',
    );

    editingId.value = null;
    editorSeed.value = emptyConfig({
        xColumn: groupable[0]?.name ?? numeric[0]?.name ?? '',
        yColumn: numeric[0]?.name ?? '',
        columns: numeric.slice(0, 4).map((column) => column.name),
    });
    editorOpen.value = true;
}

function startEdit(chart) {
    editingId.value = chart.id;
    editorSeed.value = { ...chart.config };
    editorOpen.value = true;
}

function closeEditor() {
    editorOpen.value = false;
    editingId.value = null;
}

function save(config) {
    const result = buildChart(analysis.value.table, profile.value, config);

    if (!result.ok) {
        toast.push(result.message, 'warning');

        return;
    }

    if (editingId.value === null) {
        visualizationStore.add(datasetStore.selectedId, config);
        toast.push('Grafik ditambahkan.');
    } else {
        visualizationStore.update(datasetStore.selectedId, editingId.value, config);
        toast.push('Grafik diperbarui.');
    }

    if (result.chart.note) {
        toast.push(result.chart.note, 'info');
    }

    closeEditor();
}

function removeChart(chart) {
    visualizationStore.remove(datasetStore.selectedId, chart.id);

    if (editingId.value === chart.id) {
        closeEditor();
    }

    toast.push('Grafik dihapus.', 'info');
}

function restoreAuto() {
    visualizationStore.resetToAuto(
        datasetStore.selectedId,
        autoChartConfigs(profile.value, analysis.value.table),
    );
    closeEditor();
    toast.push('Susunan grafik dikembalikan ke pilihan sistem.');
}

// Panel yang sedang diubah diberi cincin aksen agar jelas formulir di bawahnya
// milik grafik yang mana.
const editingRing = (id) =>
    editingId.value === id
        ? 'ring-1 ring-accent dark:ring-accent-dark'
        : '';

/*
 * Susunan awal diisi sekali per dataset; mengisinya di `watch` dan bukan di
 * computed supaya render tidak mengubah state.
 *
 * Ditaruh setelah seluruh state di atas dideklarasikan: `immediate` menjalankan
 * callback-nya saat setup, dan memanggil `closeEditor()` sebelum `editorOpen`
 * sempat terbentuk akan melempar ReferenceError yang mengosongkan halaman.
 */
watch(
    () => datasetStore.selectedId,
    (id) => {
        visualizationStore.ensure(
            id,
            autoChartConfigs(profile.value, analysis.value.table),
        );
        closeEditor();
    },
    { immediate: true },
);
</script>

<template>
    <AppLayout>
        <PageHeader
            title="Visualisasi"
            description="Grafik dipilihkan sistem dari hasil profiling, dan setiap panel bisa Anda ubah sendiri: jenis grafik, sumbu, agregasi, warna, dan filter."
            :breadcrumbs="[
                { label: 'Dashboard', to: { name: 'dashboard' } },
                { label: 'Visualisasi' },
            ]"
        >
            <template #actions>
                <DatasetSelector />
                <AppButton icon="refresh" @click="restoreAuto">
                    Pulihkan Otomatis
                </AppButton>
                <AppButton variant="primary" icon="plus" @click="startCreate">
                    Buat Grafik
                </AppButton>
            </template>
        </PageHeader>

        <!-- Grafik baru: tepat di bawah tombol yang memunculkannya -->
        <ChartEditor
            v-if="editorOpen && editingId === null"
            class="mb-4"
            is-new
            :profile="profile"
            :config="editorSeed"
            @save="save"
            @cancel="closeEditor"
        />

        <AppCard v-if="!charts.length" flush>
            <EmptyState
                icon="visualization"
                title="Belum ada grafik"
                description="Buat grafik sendiri, atau pulihkan susunan yang dipilihkan sistem dari hasil profiling."
            >
                <template #action>
                    <div class="flex flex-wrap items-center justify-center gap-2">
                        <AppButton icon="refresh" @click="restoreAuto">
                            Pulihkan Otomatis
                        </AppButton>
                        <AppButton variant="primary" icon="plus" @click="startCreate">
                            Buat Grafik
                        </AppButton>
                    </div>
                </template>
            </EmptyState>
        </AppCard>

        <div v-else class="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <template v-for="chart in charts" :key="chart.id">
                <!-- Panel yang konfigurasinya tidak lagi cocok dengan dataset
                     tetap ditampilkan beserta alasannya, supaya bisa diperbaiki
                     lewat tombol ubah dan tidak hilang tanpa penjelasan. -->
                <AppCard
                    v-if="!chart.built.ok"
                    title="Grafik tidak dapat digambar"
                    :class="editingRing(chart.id)"
                >
                    <template #actions>
                        <div class="flex items-center gap-1">
                            <button
                                type="button"
                                class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-ink dark:hover:text-ink-dark"
                                title="Ubah grafik"
                                @click="startEdit(chart)"
                            >
                                <AppIcon name="pencil" class="h-4 w-4" />
                                <span class="sr-only">Ubah grafik</span>
                            </button>
                            <button
                                type="button"
                                class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-status-critical"
                                title="Hapus grafik"
                                @click="removeChart(chart)"
                            >
                                <AppIcon name="trash" class="h-4 w-4" />
                                <span class="sr-only">Hapus grafik</span>
                            </button>
                        </div>
                    </template>

                    <p class="flex items-start gap-2 text-sm text-ink-2 dark:text-ink-2-dark">
                        <AppIcon
                            name="warning"
                            class="mt-0.5 h-4 w-4 shrink-0 text-[#8a5a00] dark:text-status-warning"
                        />
                        {{ chart.built.message }}
                    </p>
                </AppCard>

                <ChartPanel
                    v-else-if="chart.built.chart.render === 'panel'"
                    :title="chart.built.title"
                    :subtitle="chart.built.subtitle"
                    :type="chart.built.chart.type"
                    :labels="chart.built.chart.labels"
                    :series="chart.built.chart.series"
                    :horizontal="chart.built.chart.horizontal ?? false"
                    :height="280"
                    :class="editingRing(chart.id)"
                >
                    <template #actions>
                        <button
                            type="button"
                            class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-ink dark:hover:text-ink-dark"
                            title="Ubah grafik"
                            @click="startEdit(chart)"
                        >
                            <AppIcon name="pencil" class="h-4 w-4" />
                            <span class="sr-only">Ubah {{ chart.built.title }}</span>
                        </button>
                        <button
                            type="button"
                            class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-status-critical"
                            title="Hapus grafik"
                            @click="removeChart(chart)"
                        >
                            <AppIcon name="trash" class="h-4 w-4" />
                            <span class="sr-only">Hapus {{ chart.built.title }}</span>
                        </button>
                    </template>
                </ChartPanel>

                <div
                    v-else
                    :class="chart.built.chart.render === 'heatmap' ? 'lg:col-span-2' : ''"
                >
                    <AppCard
                        :title="chart.built.title"
                        :subtitle="chart.built.subtitle"
                        :class="editingRing(chart.id)"
                    >
                        <template #actions>
                            <div class="flex items-center gap-1">
                                <button
                                    type="button"
                                    class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-ink dark:hover:text-ink-dark"
                                    title="Ubah grafik"
                                    @click="startEdit(chart)"
                                >
                                    <AppIcon name="pencil" class="h-4 w-4" />
                                    <span class="sr-only">Ubah {{ chart.built.title }}</span>
                                </button>
                                <button
                                    type="button"
                                    class="focus-ring rounded-md p-1.5 text-ink-3 transition-colors hover:text-status-critical"
                                    title="Hapus grafik"
                                    @click="removeChart(chart)"
                                >
                                    <AppIcon name="trash" class="h-4 w-4" />
                                    <span class="sr-only">Hapus {{ chart.built.title }}</span>
                                </button>
                            </div>
                        </template>

                        <BoxPlot
                            v-if="chart.built.chart.render === 'box'"
                            :boxes="chart.built.chart.boxes"
                        />
                        <CorrelationHeatmap
                            v-else
                            :columns="chart.built.chart.columns"
                            :matrix="chart.built.chart.matrix"
                        />
                    </AppCard>
                </div>

                <!-- Formulir menyusul tepat setelah panelnya, melebar penuh -->
                <ChartEditor
                    v-if="editorOpen && editingId === chart.id"
                    :key="`editor-${chart.id}`"
                    class="lg:col-span-2"
                    :profile="profile"
                    :config="editorSeed"
                    @save="save"
                    @cancel="closeEditor"
                />
            </template>
        </div>
    </AppLayout>
</template>
