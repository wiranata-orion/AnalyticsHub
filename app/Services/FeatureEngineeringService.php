<?php

namespace App\Services;

use App\Models\Dataset;
use App\Models\FeatureSet;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

/*
 * Feature Engineering: menghasilkan salinan dataset yang sudah ditransformasi.
 *
 * Hasilnya dicatat sebagai FeatureSet tersendiri, bukan menimpa dataset asli,
 * supaya satu dataset bisa punya beberapa versi fitur dan semuanya tetap dapat
 * dipilih saat melatih model.
 */
class FeatureEngineeringService
{
    public function __construct(
        private readonly PythonEngine $engine,
        private readonly DatasetService $datasets,
    ) {
    }

    public function transform(Dataset $dataset, array $input): FeatureSet
    {
        // Lokasi diturunkan dari disk Storage, bukan storage_path(): sejak
        // Laravel 11 root disk `local` adalah storage/app/private, sehingga
        // menulis dan membaca lewat dua cara berbeda akan menunjuk folder
        // berbeda dan berkasnya seolah hilang.
        $relative = 'features/'.Str::uuid().'.csv';
        $absolute = Storage::disk(config('python.dataset_disk'))->path($relative);

        $result = $this->engine->run('feature.transform', $this->datasets->engineParams($dataset, [
            'steps' => $input['steps'],
            'target' => $input['target'] ?? null,
            'output_path' => $absolute,
        ]))['data'];

        return FeatureSet::create([
            'dataset_id' => $dataset->id,
            'name' => $input['name'] ?? 'Feature set '.now()->format('d M H:i'),
            'path' => $relative,
            'steps' => $result['steps'],
            'columns' => $result['columns'],
            'row_count' => $result['row_count'],
            'column_count' => $result['column_count'],
        ]);
    }

    public function selection(Dataset $dataset, string $target, int $topK = 10): array
    {
        return $this->engine->run('feature.selection', $this->datasets->engineParams($dataset, [
            'target' => $target,
            'top_k' => $topK,
        ]))['data'];
    }
}
