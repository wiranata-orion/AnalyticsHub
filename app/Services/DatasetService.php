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

    public function localDatasetMetadata(string $id): array
    {
        $disk = Storage::disk(config('python.dataset_disk'));
        $filename = basename($id);
        $jsonPath = 'datasets/'.$filename.'.json';

        if (! $disk->exists($jsonPath)) {
            throw new \RuntimeException("Dataset tidak ditemukan: {$filename}");
        }

        $metadata = json_decode($disk->get($jsonPath), true);

        if (! is_array($metadata)) {
            throw new \RuntimeException("Metadata dataset rusak: {$filename}");
        }

        return $metadata;
    }

    public function localEngineParams(string $id, array $extra = []): array
    {
        $metadata = $this->localDatasetMetadata($id);
        $filename = basename($id);

        return array_merge([
            'path' => Storage::disk(config('python.dataset_disk'))->path('datasets/'.$filename),
            'delimiter' => $metadata['delimiter'] ?? ',',
            'encoding' => $metadata['encoding'] ?? 'UTF-8',
            'has_header' => $metadata['has_header'] ?? true,
        ], $extra);
    }

    public function localCleaningPreview(string $id): array
    {
        $metadata = $this->localDatasetMetadata($id);
        $columns = collect($metadata['columns'] ?? []);
        $missingColumns = $columns
            ->filter(static fn (array $column) => (int) ($column['missing_count'] ?? 0) > 0)
            ->sortByDesc(static fn (array $column) => (int) ($column['missing_count'] ?? 0))
            ->values();
        $numericColumns = collect($metadata['numeric_columns'] ?? []);
        $textColumns = $columns->filter(static fn (array $column) => in_array($column['type'] ?? null, ['text', 'category'], true))->values();
        $missingCount = (int) ($metadata['missing_cells'] ?? $columns->sum('missing_count') ?? 0);
        $duplicateCount = (int) ($metadata['duplicate_rows'] ?? 0);
        $outlierCount = (int) round(($metadata['outlier_ratio'] ?? 0) * max((int) ($metadata['rows'] ?? 0), 1));
        $textCount = count(array_filter($metadata['columns'] ?? [], static fn ($column) => in_array($column['type'] ?? null, ['text'], true)));

        $missingDetails = $missingColumns->map(static function (array $column): array {
            $type = $column['type'] ?? 'unknown';
            $recommendedValue = in_array($type, ['integer', 'float'], true) ? '0' : 'Unknown';
            $recommendedStrategy = in_array($type, ['integer', 'float'], true) ? 'median' : 'mode';

            return [
                'column' => $column['name'] ?? '-',
                'type' => $type,
                'missing_count' => (int) ($column['missing_count'] ?? 0),
                'recommended_strategy' => $recommendedStrategy,
                'recommended_custom_value' => $recommendedValue,
            ];
        })->all();

        $missingHint = $missingDetails
            ? 'Kolom terdampak: '.collect($missingDetails)->take(4)->map(static fn (array $item) => $item['column'].' ('.$item['missing_count'].')')->join(', ').(count($missingDetails) > 4 ? ', ...' : '').'.'
            : 'Tidak ada missing value yang terdeteksi.';

        $missingCustomHint = $missingDetails
            ? collect($missingDetails)->take(4)->map(static fn (array $item) => $item['column'].': '.$item['recommended_custom_value'])->join(' | ')
            : 'Gunakan nilai yang konsisten untuk semua kolom yang dipilih.';

        $missingColumnOptions = $missingDetails;

        $issues = [
            [
                'key' => 'missing',
                'icon' => 'warning',
                'tone' => 'serious',
                'title' => 'Missing Values',
                'count' => $missingCount,
                'unit' => 'sel',
                'description' => 'Nilai kosong tersebar di beberapa kolom dataset.',
                'hint' => $missingHint,
                'details' => $missingDetails,
            ],
            [
                'key' => 'duplicate',
                'icon' => 'copy',
                'tone' => 'warning',
                'title' => 'Duplikat',
                'count' => $duplicateCount,
                'unit' => 'baris',
                'description' => 'Baris identik terdeteksi pada dataset aktif.',
                'hint' => 'Duplikat dihitung dari isi baris yang sama pada kolom non-identitas.',
                'details' => $columns
                    ->filter(static fn (array $column) => ! in_array($column['type'] ?? null, ['id', 'identifier'], true))
                    ->take(5)
                    ->map(static fn (array $column): array => [
                        'column' => $column['name'] ?? '-',
                        'type' => $column['type'] ?? 'unknown',
                    ])
                    ->values()
                    ->all(),
            ],
            [
                'key' => 'outlier',
                'icon' => 'chart',
                'tone' => 'warning',
                'title' => 'Outliers',
                'count' => $outlierCount,
                'unit' => 'indikasi',
                'description' => 'Kolom numerik mengandung nilai ekstrem yang perlu ditinjau.',
                'hint' => $numericColumns->isNotEmpty()
                    ? 'Kolom numerik terdeteksi: '.$numericColumns->take(5)->implode(', ').($numericColumns->count() > 5 ? ', ...' : '').'.'
                    : 'Tidak ada kolom numerik yang bisa dianalisis.',
                'details' => $numericColumns
                    ->take(6)
                    ->map(static fn (string $name): array => [
                        'column' => $name,
                        'type' => 'numeric',
                    ])
                    ->values()
                    ->all(),
            ],
            [
                'key' => 'type',
                'icon' => 'document',
                'tone' => 'critical',
                'title' => 'Tipe Tidak Cocok',
                'count' => $textCount,
                'unit' => 'kolom',
                'description' => 'Kolom teks/kategori bisa dibersihkan dan dinormalisasi.',
                'hint' => $textColumns->isNotEmpty()
                    ? 'Kolom teks/kategori: '.$textColumns->take(5)->map(static fn (array $column) => $column['name'] ?? '-')->join(', ').($textColumns->count() > 5 ? ', ...' : '').'.'
                    : 'Tidak ada kolom teks untuk dinormalisasi.',
                'details' => $textColumns
                    ->take(6)
                    ->map(static fn (array $column): array => [
                        'column' => $column['name'] ?? '-',
                        'type' => $column['type'] ?? 'unknown',
                    ])
                    ->values()
                    ->all(),
            ],
        ];

        $issues = array_values(array_filter($issues, static fn (array $issue) => (int) ($issue['count'] ?? 0) > 0));

        $strategies = array_values(array_filter([
            $missingCount > 0 ? [
                'key' => 'missing',
                'label' => 'Missing Values',
                'options' => ['median', 'mode', 'drop_rows', 'forward_fill', 'backward_fill', 'custom_value'],
                'selected' => 'median',
            ] : null,
            $duplicateCount > 0 ? [
                'key' => 'duplicate',
                'label' => 'Duplikat',
                'options' => ['keep_first', 'keep_last', 'drop_all'],
                'selected' => 'keep_first',
            ] : null,
            $outlierCount > 0 ? [
                'key' => 'outlier',
                'label' => 'Outliers',
                'options' => ['keep', 'winsorize', 'iqr_remove', 'zscore_remove'],
                'selected' => 'winsorize',
            ] : null,
            $textCount > 0 ? [
                'key' => 'text',
                'label' => 'Normalisasi Teks',
                'options' => ['trim', 'lower', 'upper', 'title'],
                'selected' => 'trim',
            ] : null,
        ]));

        return [
            'issues' => $issues,
            'strategies' => $strategies,
            'missing_hint' => $missingHint,
            'missing_custom_hint' => $missingCustomHint,
            'missing_columns' => $missingColumnOptions,
            'impact' => [
                'labels' => ['Sebelum', 'Sesudah'],
                'series' => [
                    ['label' => 'Baris Valid', 'data' => [(int) ($metadata['rows'] ?? 0), (int) ($metadata['rows'] ?? 0)]],
                    ['label' => 'Baris Bermasalah', 'data' => [(int) ($metadata['duplicate_rows'] ?? 0) + (int) ($metadata['missing_cells'] ?? 0), 0]],
                ],
            ],
            'preview' => [
                'before' => $metadata['problematic_preview'] ?? $metadata['preview'] ?? null,
                'after' => null,
            ],
            'selected' => [
                'missing' => $missingCount > 0 ? 'median' : null,
                'duplicate' => $duplicateCount > 0 ? 'keep_first' : null,
                'outlier' => $outlierCount > 0 ? 'winsorize' : null,
                'text' => $textCount > 0 ? 'trim' : null,
            ],
        ];
    }

    public function localCleaningOutputPath(string $id): string
    {
        $filename = basename($id);

        return Storage::disk(config('python.dataset_disk'))->path('cleaning/'.$filename.'.csv');
    }

    public function cleanLocal(string $id, array $strategies = []): array
    {
        $metadata = $this->localDatasetMetadata($id);
        $outputPath = $this->localCleaningOutputPath($id);

        $outcome = $this->engine->run('dataset.clean', array_merge(
            $this->localEngineParams($id),
            [
                'strategies' => $strategies,
                'output_path' => $outputPath,
            ],
        ));

        return array_merge($outcome['data'], [
            'output_path' => $outputPath,
            'dataset' => [
                'id' => $metadata['id'] ?? basename($id),
                'name' => $metadata['name'] ?? basename($id),
            ],
        ]);
    }

    public function storeLocalDatasetMetadata(string $id, array $metadata): void
    {
        Storage::disk(config('python.dataset_disk'))->put(
            'datasets/'.basename($id).'.json',
            json_encode($metadata, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
        );
    }

    public function profileLocal(string $id): array
    {
        $metadata = $this->localDatasetMetadata($id);
        $outcome = $this->engine->run('dataset.profile', $this->localEngineParams($id));
        $profile = $outcome['data'];

        $updated = array_merge($metadata, [
            'id' => basename($id),
            'path' => $metadata['path'] ?? basename($id),
            'rows' => $profile['row_count'] ?? 0,
            'columns_count' => $profile['column_count'] ?? 0,
            'missing_cells' => $profile['missing_cells'] ?? 0,
            'duplicate_rows' => $profile['duplicate_rows'] ?? 0,
            'outlier_ratio' => $profile['outlier_ratio'] ?? 0,
            'numeric_columns' => $profile['numeric_columns'] ?? [],
            'categorical_columns' => $profile['categorical_columns'] ?? [],
            'datetime_columns' => $profile['datetime_columns'] ?? [],
            'identifier_columns' => $profile['identifier_columns'] ?? [],
            'preview' => $profile['preview'] ?? null,
                'problematic_preview' => $profile['problematic_preview'] ?? $profile['preview'] ?? null,
            'status' => 'ready',
            'error_message' => null,
            'columns' => collect($profile['columns'] ?? [])->map(fn ($column) => [
                'name' => $column['name'],
                'type' => $column['type'],
                'missing' => (float) ($column['missing_percent'] ?? 0),
                'missing_count' => $column['missing_count'] ?? 0,
                'unique' => $column['unique_count'] ?? 0,
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
            ])->toArray(),
            'updated_at' => now()->format('d M Y'),
        ]);

        $this->storeLocalDatasetMetadata($id, $updated);

        return $updated;
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
