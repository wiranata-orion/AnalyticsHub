<?php

namespace App\Services;

use App\Models\AnalysisRun;
use App\Models\Dataset;

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
        Dataset $dataset,
        string $kind,
        string $variant,
        string $command,
        array $params = [],
    ): AnalysisRun {
        $run = AnalysisRun::create([
            'dataset_id' => $dataset->id,
            'kind' => $kind,
            'variant' => $variant,
            'params' => $params,
            'status' => 'running',
        ]);

        try {
            $outcome = $this->engine->run(
                $command,
                $this->datasets->engineParams($dataset, $params),
            );

            $run->update([
                'result' => json_encode($outcome['data'], JSON_UNESCAPED_UNICODE),
                'status' => 'ready',
                'duration_ms' => $outcome['duration_ms'],
            ]);
        } catch (\Throwable $error) {
            $run->update(['status' => 'failed', 'error_message' => $error->getMessage()]);

            throw $error;
        }

        return $run->fresh();
    }

    /** Hasil terakhir yang berhasil, untuk mengisi halaman tanpa menghitung ulang. */
    public function latest(Dataset $dataset, string $kind, ?string $variant = null): ?AnalysisRun
    {
        return $dataset->analysisRuns()->latestOf($kind, $variant)->first();
    }

    /**
     * Jalankan bila belum pernah, atau ambil hasil tersimpan bila parameternya sama.
     *
     * Dipakai analisis yang mahal (AutoML, forecasting) supaya membuka ulang
     * halaman tidak memicu perhitungan berat yang sama untuk kedua kalinya.
     */
    public function cached(
        Dataset $dataset,
        string $kind,
        string $variant,
        string $command,
        array $params = [],
    ): AnalysisRun {
        $existing = $this->latest($dataset, $kind, $variant);

        if ($existing && $existing->params == $params) {
            return $existing;
        }

        return $this->run($dataset, $kind, $variant, $command, $params);
    }
}
