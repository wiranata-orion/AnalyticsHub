<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AnalysisRun extends Model
{
    protected $fillable = [
        'dataset_id',
        'kind',
        'variant',
        'params',
        'result',
        'status',
        'error_message',
        'duration_ms',
    ];

    protected function casts(): array
    {
        return [
            'params' => 'array',
            // `result` sengaja tidak di-cast array: ukurannya bisa besar dan
            // sebagian besar pemakaian hanya meneruskannya apa adanya ke klien.
            'duration_ms' => 'integer',
        ];
    }

    public function dataset(): BelongsTo
    {
        return $this->belongsTo(Dataset::class);
    }

    /** Hasil sebagai array; null bila analisisnya gagal atau belum selesai. */
    public function resultArray(): ?array
    {
        return $this->result ? json_decode($this->result, true) : null;
    }

    public function scopeLatestOf($query, string $kind, ?string $variant = null)
    {
        return $query->where('kind', $kind)
            ->when($variant, fn ($q) => $q->where('variant', $variant))
            ->where('status', 'ready')
            ->latest('id');
    }
}
