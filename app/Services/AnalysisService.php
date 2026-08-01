<?php

namespace App\Services;

use Illuminate\Support\Facades\Storage;

/*
 * Menjalankan analisis dan menyimpan hasilnya.
 *
 * Seluruh fitur analisis melewati kelas ini, bukan memanggil PythonEngine
 * langsung, karena tiga hal selalu perlu dilakukan bersama-sama: menjalankan
 * perintah, mencatat hasilnya, dan menandai kegagalan. Menyalin ketiganya ke
 * setiap controller hanya menunggu salah satunya terlupa.
 *
 * Efek sampingnya justru yang paling berguna: karena setiap eksekusi tercatat,
 * halaman yang dibuka ulang bisa langsung menampilkan hasil terakhir tanpa
 * menghitung ulang.
 */
class AnalysisService
{
    public function __construct(
        private readonly PythonEngine $engine,
        private readonly DatasetService $datasets,
    ) {
    }

    /**
     * @param  string  $kind     kelompok analisis (eda, statistics, mining, ...)
     * @param  string  $variant  sub-jenis (univariate, t_test, clustering, ...)
     * @param  string  $command  perintah engine Python
     */
    public function run(
        string $datasetId,
        string $kind,
        string $variant,
        string $command,
        array $params = [],
    ): array {
        $outcome = $this->engine->run(
            $command,
            $this->datasets->localEngineParams($datasetId, $params),
        );

        $payload = [
            'data' => $outcome['data'],
            'meta' => [
                'run_id' => null,
                'duration_ms' => $outcome['duration_ms'],
                'ran_at' => now()->toIso8601String(),
                'params' => $params,
            ],
        ];

        $this->storeLocalResult($datasetId, $kind, $variant, $payload);

        return $payload;
    }

    /** Hasil terakhir yang berhasil, untuk mengisi halaman tanpa menghitung ulang. */
    public function latest(string $datasetId, string $kind, ?string $variant = null): ?array
    {
        return $this->loadLocalResult($datasetId, $kind, $variant);
    }

    /**
     * Jalankan bila belum pernah, atau ambil hasil tersimpan bila parameternya sama.
     *
     * Dipakai analisis yang mahal (AutoML, forecasting) supaya membuka ulang
     * halaman tidak memicu perhitungan berat yang sama untuk kedua kalinya.
     */
    public function cached(
        string $datasetId,
        string $kind,
        string $variant,
        string $command,
        array $params = [],
    ): array {
        $existing = $this->latest($datasetId, $kind, $variant);

        if ($existing && (($existing['meta']['params'] ?? null) == $params)) {
            return $existing;
        }

        return $this->run($datasetId, $kind, $variant, $command, $params);
    }

    private function resultPath(string $datasetId, string $kind, ?string $variant = null): string
    {
        $datasetKey = basename($datasetId);
        $kindKey = preg_replace('/[^A-Za-z0-9._-]/', '_', $kind) ?: 'analysis';
        $variantKey = preg_replace('/[^A-Za-z0-9._-]/', '_', $variant ?? 'default') ?: 'default';

        return 'analysis/'.$datasetKey.'/'.$kindKey.'/'.$variantKey.'.json';
    }

    private function storeLocalResult(string $datasetId, string $kind, string $variant, array $payload): void
    {
        Storage::disk(config('python.dataset_disk'))->put(
            $this->resultPath($datasetId, $kind, $variant),
            json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
        );
    }

    private function loadLocalResult(string $datasetId, string $kind, ?string $variant = null): ?array
    {
        $disk = Storage::disk(config('python.dataset_disk'));
        $path = $this->resultPath($datasetId, $kind, $variant);

        if (! $disk->exists($path)) {
            return null;
        }

        $decoded = json_decode($disk->get($path), true);

        return is_array($decoded) ? $decoded : null;
    }
}
