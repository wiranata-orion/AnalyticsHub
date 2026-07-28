<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import PageHeader from '@/Components/UI/PageHeader.vue';
import AppCard from '@/Components/UI/AppCard.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppIcon from '@/Components/UI/AppIcon.vue';
import { useDatasetStore } from '@/stores/dataset';
import { useToastStore } from '@/stores/toast';

/*
 * Halaman unggah. Pemilihan berkas dan validasi dasar berjalan di klien;
 * pengiriman ke server menunggu endpoint REST `POST /api/datasets`. Sementara
 * itu berkas didaftarkan ke store agar seluruh alur (daftar → profiling)
 * tetap bisa dicoba ujung ke ujung.
 */
const ACCEPTED = ['.csv', '.xlsx', '.xls'];
const MAX_MB = 200;

const file = ref(null);
const isDragging = ref(false);
const errorMessage = ref(null);
const fileInput = ref(null);

const options = ref({
    delimiter: ',',
    encoding: 'UTF-8',
    hasHeader: true,
});

function formatSize(bytes) {
    const mb = bytes / (1024 * 1024);

    return mb < 1
        ? `${Math.round(bytes / 1024)} KB`
        : `${mb.toFixed(1).replace('.', ',')} MB`;
}

function selectFile(candidate) {
    errorMessage.value = null;

    if (!candidate) {
        return;
    }

    const extension = candidate.name
        .slice(candidate.name.lastIndexOf('.'))
        .toLowerCase();

    if (!ACCEPTED.includes(extension)) {
        errorMessage.value = `Format ${extension} tidak didukung. Gunakan CSV, XLSX, atau XLS.`;

        return;
    }

    if (candidate.size > MAX_MB * 1024 * 1024) {
        errorMessage.value = `Ukuran berkas melebihi ${MAX_MB} MB.`;

        return;
    }

    file.value = candidate;
}

function handleDrop(event) {
    isDragging.value = false;
    selectFile(event.dataTransfer.files[0]);
}

function clearFile() {
    file.value = null;
    errorMessage.value = null;

    if (fileInput.value) {
        fileInput.value.value = '';
    }
}

const router = useRouter();
const datasetStore = useDatasetStore();
const toast = useToastStore();

const isUploading = ref(false);
const uploadProgress = ref(0);

/*
 * Unggahan sungguhan: berkas dikirim ke POST /api/datasets, disimpan di storage
 * server, lalu langsung diprofiling engine Python. Permintaan baru selesai
 * setelah profiling rampung, jadi dataset yang muncul di daftar selalu siap
 * dianalisis.
 */
async function submit() {
    if (!file.value || isUploading.value) {
        return;
    }

    isUploading.value = true;
    uploadProgress.value = 0;

    try {
        const dataset = await datasetStore.upload(
            file.value,
            options.value,
            (percent) => (uploadProgress.value = percent),
        );

        toast.push(
            `"${dataset.name}" selesai diprofiling: ${dataset.rows?.toLocaleString('id-ID')} baris, ${dataset.columns_count} kolom.`,
        );
        router.push({ name: 'datasets.index' });
    } catch (error) {
        toast.push(error.message, 'warning');
    } finally {
        isUploading.value = false;
    }
}
</script>

<template>
    <PageHeader
        title="Upload Dataset"
        description="Unggah berkas CSV atau Excel untuk mulai dianalisis."
        :breadcrumbs="[
            { label: 'Dashboard', to: { name: 'dashboard' } },
            { label: 'Dataset', to: { name: 'datasets.index' } },
            { label: 'Upload' },
        ]"
    />

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div class="space-y-4 lg:col-span-2">
            <AppCard>
                <!-- Dropzone -->
                <div
                    class="rounded-xl border-2 border-dashed p-8 text-center transition-colors"
                    :class="
                        isDragging
                            ? 'border-accent bg-accent/5 dark:border-accent-dark'
                            : 'border-hairline dark:border-hairline-dark'
                    "
                    @dragover.prevent="isDragging = true"
                    @dragleave.prevent="isDragging = false"
                    @drop.prevent="handleDrop"
                >
                    <div
                        class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-plane text-ink-3 dark:bg-raised-dark"
                    >
                        <AppIcon name="upload" class="h-5 w-5" />
                    </div>

                    <p class="mt-4 text-sm font-medium text-ink dark:text-ink-dark">
                        Tarik berkas ke sini
                    </p>
                    <p class="mt-1 text-sm text-ink-2 dark:text-ink-2-dark">
                        atau
                        <button
                            type="button"
                            class="focus-ring rounded font-medium text-accent hover:underline dark:text-accent-dark"
                            @click="fileInput.click()"
                        >
                            pilih dari komputer
                        </button>
                    </p>
                    <p class="mt-3 text-xs text-ink-3">
                        CSV, XLSX, atau XLS · maksimal {{ MAX_MB }} MB
                    </p>

                    <input
                        ref="fileInput"
                        type="file"
                        class="hidden"
                        :accept="ACCEPTED.join(',')"
                        @change="selectFile($event.target.files[0])"
                    />
                </div>

                <p
                    v-if="errorMessage"
                    class="mt-3 flex items-center gap-1.5 text-sm text-status-critical"
                >
                    <AppIcon name="warning" class="h-4 w-4 shrink-0" />
                    {{ errorMessage }}
                </p>

                <!-- Berkas terpilih -->
                <div
                    v-if="file"
                    class="mt-4 flex items-center gap-3 rounded-lg border border-hairline bg-plane px-4 py-3 dark:border-hairline-dark dark:bg-plane-dark"
                >
                    <AppIcon
                        name="document"
                        class="h-5 w-5 shrink-0 text-accent dark:text-accent-dark"
                    />
                    <div class="min-w-0 flex-1">
                        <p
                            class="truncate text-sm font-medium text-ink dark:text-ink-dark"
                        >
                            {{ file.name }}
                        </p>
                        <p class="text-xs tabular-nums text-ink-3">
                            {{ formatSize(file.size) }}
                        </p>
                    </div>
                    <button
                        type="button"
                        class="focus-ring shrink-0 rounded-md p-1.5 text-ink-3 transition-colors hover:text-status-critical"
                        @click="clearFile"
                    >
                        <AppIcon name="close" class="h-4 w-4" />
                        <span class="sr-only">Hapus berkas</span>
                    </button>
                </div>
            </AppCard>

            <AppCard
                title="Opsi Impor"
                subtitle="Sesuaikan bila berkas tidak terbaca dengan benar."
            >
                <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                        <label
                            for="import-delimiter"
                            class="block text-sm font-medium text-ink-2 dark:text-ink-2-dark"
                        >
                            Pemisah Kolom
                        </label>
                        <select
                            id="import-delimiter"
                            v-model="options.delimiter"
                            class="focus-ring mt-1.5 h-9 w-full rounded-lg border-hairline bg-surface py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                        >
                            <option value=",">Koma ( , )</option>
                            <option value=";">Titik koma ( ; )</option>
                            <option value="\t">Tab</option>
                            <option value="|">Pipa ( | )</option>
                        </select>
                    </div>

                    <div>
                        <label
                            for="import-encoding"
                            class="block text-sm font-medium text-ink-2 dark:text-ink-2-dark"
                        >
                            Encoding
                        </label>
                        <select
                            id="import-encoding"
                            v-model="options.encoding"
                            class="focus-ring mt-1.5 h-9 w-full rounded-lg border-hairline bg-surface py-0 text-sm text-ink focus:border-hairline focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark dark:text-ink-dark"
                        >
                            <option>UTF-8</option>
                            <option>UTF-16</option>
                            <option>ISO-8859-1</option>
                            <option>Windows-1252</option>
                        </select>
                    </div>
                </div>

                <label class="mt-4 flex items-center gap-2.5">
                    <input
                        v-model="options.hasHeader"
                        type="checkbox"
                        class="focus-ring h-4 w-4 rounded border-hairline text-accent focus:ring-0 dark:border-hairline-dark dark:bg-plane-dark"
                    />
                    <span class="text-sm text-ink-2 dark:text-ink-2-dark">
                        Baris pertama adalah nama kolom
                    </span>
                </label>

                <template #footer>
                    <div class="flex flex-wrap items-center justify-end gap-3">
                        <p v-if="isUploading" class="mr-auto text-xs tabular-nums text-ink-2 dark:text-ink-2-dark">
                            {{ uploadProgress < 100
                                ? `Mengunggah… ${uploadProgress}%`
                                : 'Profiling berjalan di server…' }}
                        </p>
                        <AppButton :to="{ name: 'datasets.index' }">
                            Batal
                        </AppButton>
                        <AppButton
                            variant="primary"
                            icon="upload"
                            :disabled="!file || isUploading"
                            @click="submit"
                        >
                            {{ isUploading ? 'Memproses…' : 'Unggah & Analisis' }}
                        </AppButton>
                    </div>
                </template>
            </AppCard>
        </div>

        <AppCard title="Yang Terjadi Setelah Unggah">
            <ol class="space-y-4">
                <li
                    v-for="(step, index) in [
                        {
                            title: 'Validasi berkas',
                            body: 'Format, ukuran, dan struktur kolom diperiksa.',
                        },
                        {
                            title: 'Data profiling',
                            body: 'Tipe data, missing value, duplikat, dan outlier dihitung.',
                        },
                        {
                            title: 'Rekomendasi cleaning',
                            body: 'Sistem mengusulkan langkah pembersihan yang sesuai.',
                        },
                        {
                            title: 'Siap dianalisis',
                            body: 'Dataset dapat dipakai untuk visualisasi, mining, dan model.',
                        },
                    ]"
                    :key="step.title"
                    class="flex gap-3"
                >
                    <span
                        class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-plane text-xs font-semibold tabular-nums text-ink-2 dark:bg-raised-dark dark:text-ink-2-dark"
                    >
                        {{ index + 1 }}
                    </span>
                    <div class="min-w-0">
                        <p class="text-sm font-medium text-ink dark:text-ink-dark">
                            {{ step.title }}
                        </p>
                        <p class="mt-0.5 text-sm text-ink-2 dark:text-ink-2-dark">
                            {{ step.body }}
                        </p>
                    </div>
                </li>
            </ol>
        </AppCard>
    </div>
</template>
