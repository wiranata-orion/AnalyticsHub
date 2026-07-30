<?php

namespace App\Services;

use App\Models\Dataset;
use App\Models\DatasetColumn;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

/*
 * Siklus hidup dataset: unggah, profiling, dan penghapusan.
 *
 * Profiling dijalankan segera setelah unggah karena hampir semua fitur lain
 * bergantung padanya — daftar kolom numerik, kandidat target, dan tipe data
 * dibaca dari tabel `dataset_columns`, bukan dengan membuka ulang berkasnya.
 */
class DatasetService
{
    public function __construct(private readonly PythonEngine $engine)
    {
    }

    # Mengunggah berkas dataset, menulis metadata ke database, dan menjalankan profiling.
    public function store(UploadedFile $file, array $options = []): array
    {
        $diskName = config('python.dataset_disk');
        $disk = Storage::disk($diskName);
        
        $extension = strtolower($file->getClientOriginalExtension());
        $storedName = Str::uuid().'.'.$extension;

        // 1. Simpan file fisik ke folder storage lokal
        $path = $file->storeAs('datasets', $storedName, $diskName);
        
        // 2. Dapatkan path absolut (C:\...\storage\app\...) untuk dibaca Python
        $absolutePath = $disk->path($path);

        // 3. Susun parameter untuk Python
        $params = [
            'path' => $absolutePath,
            'delimiter' => $options['delimiter'] ?? ',',
            'encoding' => $options['encoding'] ?? 'UTF-8',
            'has_header' => $options['has_header'] ?? true,
        ];

        try {
            // 4. Jalankan script Python
            $outcome = $this->engine->run('dataset.profile', $params);
            
            // 5. Kembalikan data mentah sebagai Array
            return [
                'file_path' => $path, // Penting disimpan oleh frontend untuk dipanggil lagi nanti
                'original_name' => $file->getClientOriginalName(),
                'size_bytes' => $file->getSize(),
                'format' => strtoupper($extension),
                'profile' => $outcome['data'], // Hasil hitungan kolom dll dari Python
            ];

        } catch (\Throwable $error) {
            // Jika Python error/gagal, hapus file agar tidak jadi sampah storage
            $disk->delete($path);
            throw $error;
        }
    }

    /** Parameter baca berkas yang dikirim ke engine pada setiap perintah. */
    public function engineParams(Dataset $dataset, array $extra = []): array
    {
        return array_merge([
            'path' => $dataset->absolutePath(),
            'delimiter' => $dataset->delimiter,
            'encoding' => $dataset->encoding,
            'has_header' => $dataset->has_header,
        ], $extra);
    }

    public function profile(Dataset $dataset): Dataset
    {
        $dataset->update(['status' => 'profiling', 'error_message' => null]);

        try {
            $outcome = $this->engine->run('dataset.profile', $this->engineParams($dataset));
        } catch (\Throwable $error) {
            $dataset->update(['status' => 'failed', 'error_message' => $error->getMessage()]);

            throw $error;
        }

        $profile = $outcome['data'];

        // Kolom ditulis ulang seluruhnya: profiling ulang harus mencerminkan
        // keadaan berkas saat ini, bukan menumpuk di atas hasil sebelumnya.
        DB::transaction(function () use ($dataset, $profile) {
            $dataset->columns()->delete();

            foreach ($profile['columns'] as $column) {
                DatasetColumn::create([
                    'dataset_id' => $dataset->id,
                    'position' => $column['position'],
                    'name' => $column['name'],
                    'type' => $column['type'],
                    'missing_count' => $column['missing_count'],
                    'missing_percent' => $column['missing_percent'],
                    'unique_count' => $column['unique_count'],
                    'mean' => $column['mean'] ?? null,
                    'std' => $column['std'] ?? null,
                    'min' => $column['min'] ?? null,
                    'q1' => $column['q1'] ?? null,
                    'median' => $column['median'] ?? null,
                    'q3' => $column['q3'] ?? null,
                    'max' => $column['max'] ?? null,
                    'skewness' => $column['skewness'] ?? null,
                    'kurtosis' => $column['kurtosis'] ?? null,
                    'outlier_count' => $column['outlier_count'] ?? 0,
                    'is_identifier' => $column['is_identifier'] ?? false,
                    'top_values' => $column['top_values'] ?? null,
                ]);
            }

            $dataset->update([
                'row_count' => $profile['row_count'],
                'column_count' => $profile['column_count'],
                'status' => 'ready',
            ]);
        });

        return $dataset->fresh('columns');
    }

    public function destroy(Dataset $dataset): void
    {
        $disk = Storage::disk(config('python.dataset_disk'));

        // Berkas turunan (feature set, artefak model) ikut dibuang supaya
        // storage tidak menyimpan berkas yatim yang tak bisa dirujuk lagi.
        foreach ($dataset->featureSets as $featureSet) {
            $disk->delete($featureSet->path);
        }

        foreach ($dataset->trainedModels as $model) {
            if ($model->artifact_path) {
                $disk->delete($model->artifact_path);
            }
        }

        
        $disk->delete($dataset->path);

        $dataset->delete();
    }

    public function preview(Dataset $dataset, int $limit = 25): array
    {
        return $this->engine->run(
            'dataset.preview',
            $this->engineParams($dataset, ['limit' => $limit]),
        )['data'];
    }
}
