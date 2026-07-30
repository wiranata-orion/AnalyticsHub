<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Facades\Storage;

class FeatureSet extends Model
{
    protected $fillable = [
        'dataset_id',
        'name',
        'path',
        'steps',
        'columns',
        'row_count',
        'column_count',
    ];

    protected function casts(): array
    {
        return [
            'steps' => 'array',
            'columns' => 'array',
            'row_count' => 'integer',
            'column_count' => 'integer',
        ];
    }

    public function dataset(): BelongsTo
    {
        return $this->belongsTo(Dataset::class);
    }

    public function trainedModels(): HasMany
    {
        return $this->hasMany(TrainedModel::class);
    }

    public function absolutePath(): string
    {
        return Storage::disk(config('python.dataset_disk'))->path($this->path);
    }
}
