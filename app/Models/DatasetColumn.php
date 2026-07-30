<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class DatasetColumn extends Model
{
    protected $fillable = [
        'dataset_id',
        'position',
        'name',
        'type',
        'missing_count',
        'missing_percent',
        'unique_count',
        'mean',
        'std',
        'min',
        'q1',
        'median',
        'q3',
        'max',
        'skewness',
        'kurtosis',
        'outlier_count',
        'is_identifier',
        'top_values',
    ];

    protected function casts(): array
    {
        return [
            'missing_percent' => 'float',
            'mean' => 'float',
            'std' => 'float',
            'min' => 'float',
            'q1' => 'float',
            'median' => 'float',
            'q3' => 'float',
            'max' => 'float',
            'skewness' => 'float',
            'kurtosis' => 'float',
            'is_identifier' => 'boolean',
            'top_values' => 'array',
        ];
    }

    public function dataset(): BelongsTo
    {
        return $this->belongsTo(Dataset::class);
    }

    public function isNumeric(): bool
    {
        return in_array($this->type, ['integer', 'float'], true);
    }

    /*
     * Kandidat target klasifikasi: kategori dengan kelas sedikit. Di atas ambang
     * ini kolomnya lebih mirip identitas (kode pos, SKU) daripada label.
     */
    public function isTargetCandidate(): bool
    {
        return ! $this->is_identifier
            && $this->type === 'category'
            && $this->unique_count >= 2
            && $this->unique_count <= 12;
    }
}
