<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Facades\Storage;

class Dataset extends Model
{
    use HasFactory;

    protected $fillable = [
        'name',
        'original_name',
        'path',
        'format',
        'delimiter',
        'encoding',
        'has_header',
        'size_bytes',
        'row_count',
        'column_count',
        'status',
        'error_message',
        'uploaded_by',
    ];

    protected function casts(): array
    {
        return [
            'has_header' => 'boolean',
            'size_bytes' => 'integer',
            'row_count' => 'integer',
            'column_count' => 'integer',
        ];
    }

    public function columns(): HasMany
    {
        return $this->hasMany(DatasetColumn::class)->orderBy('position');
    }

    public function analysisRuns(): HasMany
    {
        return $this->hasMany(AnalysisRun::class);
    }

    public function featureSets(): HasMany
    {
        return $this->hasMany(FeatureSet::class);
    }

    public function trainedModels(): HasMany
    {
        return $this->hasMany(TrainedModel::class);
    }

    /** Path absolut berkas, dipakai engine Python untuk membacanya lewat pandas. */
    public function absolutePath(): string
    {
        return Storage::disk(config('python.dataset_disk'))->path($this->path);
    }

    public function isReady(): bool
    {
        return $this->status === 'ready';
    }
}
