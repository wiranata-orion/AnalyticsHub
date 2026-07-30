<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Support\Facades\Storage;

class TrainedModel extends Model
{
    protected $fillable = [
        'dataset_id',
        'feature_set_id',
        'name',
        'task',
        'algorithm',
        'target',
        'features',
        'params',
        'metrics',
        'evaluation',
        'artifact_path',
        'status',
        'error_message',
        'training_time_ms',
        'prediction_time_ms',
        'is_best',
        'automl_run_id',
    ];

    protected function casts(): array
    {
        return [
            'features' => 'array',
            'params' => 'array',
            'metrics' => 'array',
            'is_best' => 'boolean',
            'training_time_ms' => 'integer',
            'prediction_time_ms' => 'integer',
        ];
    }

    public function dataset(): BelongsTo
    {
        return $this->belongsTo(Dataset::class);
    }

    public function featureSet(): BelongsTo
    {
        return $this->belongsTo(FeatureSet::class);
    }

    public function evaluationArray(): ?array
    {
        return $this->evaluation ? json_decode($this->evaluation, true) : null;
    }

    public function absoluteArtifactPath(): ?string
    {
        return $this->artifact_path
            ? Storage::disk(config('python.dataset_disk'))->path($this->artifact_path)
            : null;
    }

    /** Metrik utama untuk ditampilkan di tabel ringkas. */
    public function headlineMetric(): array
    {
        if ($this->task === 'regression') {
            return ['label' => 'R²', 'value' => $this->metrics['r2'] ?? null];
        }

        return ['label' => 'Akurasi', 'value' => $this->metrics['accuracy'] ?? null];
    }
}
