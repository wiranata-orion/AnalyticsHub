<?php

namespace App\Services;

use App\Exceptions\PythonEngineException;
use Illuminate\Support\Facades\Log;
use Symfony\Component\Process\Exception\ProcessTimedOutException;
use Symfony\Component\Process\Process;

/*
 * Jembatan tunggal antara Laravel dan engine analisis Python.
 *
 * Seluruh perhitungan berat berjalan di proses Python terpisah. Kontraknya
 * sederhana dan sengaja dibuat satu pintu:
 *
 *   PHP  -> stdin : {"command": "eda.univariate", "params": {...}}
 *   PHON -> stdout: {"ok": true, "data": {...}}  atau  {"ok": false, "error": "..."}
 *
 * Kenapa stdin/stdout dan bukan argumen baris perintah: parameter analisis bisa
 * memuat daftar kolom, nilai filter, dan konfigurasi bertingkat. Melewatkannya
 * sebagai argumen akan berbenturan dengan escaping shell Windows, sedangkan JSON
 * lewat stdin tidak punya batas panjang praktis dan tidak perlu di-escape.
 *
 * Kelas ini TIDAK memuat logika analisis apa pun — hanya menjalankan proses,
 * menerjemahkan kegagalan, dan mencatat durasinya.
 */
class PythonEngine
{
    public function __construct(
        private readonly string $bin,
        private readonly string $entry,
        private readonly int $timeout,
    ) {
    }

    public static function fromConfig(): self
    {
        return new self(
            config('python.bin'),
            config('python.entry'),
            config('python.timeout'),
        );
    }

    /**
     * Jalankan satu perintah analisis.
     *
     * @return array{data: array, duration_ms: int}
     *
     * @throws PythonEngineException
     */
    public function run(string $command, array $params = []): array
    {
        $this->assertRunnable();

        $payload = json_encode(
            ['command' => $command, 'params' => $params],
            JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES,
        );

        /*
         * `-X utf8` mengaktifkan mode UTF-8 Python (PEP 540) sehingga stdout dan
         * stderr tidak memakai code page konsol Windows dan nama kolom non-ASCII
         * tetap utuh.
         *
         * Sengaja lewat argumen, BUKAN lewat setEnv('PYTHONIOENCODING'):
         * menyetel environment membuat proses anak kehilangan variabel bawaan
         * Windows seperti SystemRoot, dan tanpa itu inisialisasi Winsock di
         * dalam joblib/scikit-learn gagal dengan WinError 10106.
         */
        $process = new Process([$this->bin, '-X', 'utf8', '-u', $this->entry]);
        $process->setInput($payload);
        $process->setTimeout($this->timeout);
        $process->setEnv($this->essentialEnvironment());

        $startedAt = microtime(true);

        try {
            $process->run();
        } catch (ProcessTimedOutException) {
            throw new PythonEngineException(
                "Analisis '{$command}' melewati batas {$this->timeout} detik. "
                .'Coba pada dataset yang lebih kecil atau naikkan PYTHON_TIMEOUT.',
            );
        }

        $durationMs = (int) round((microtime(true) - $startedAt) * 1000);
        $stdout = trim($process->getOutput());
        $stderr = trim($process->getErrorOutput());

        if (! $process->isSuccessful() && $stdout === '') {
            Log::error('Engine Python gagal', compact('command', 'stderr'));

            throw new PythonEngineException(
                $this->readableFailure($command, $stderr, $process->getExitCode()),
            );
        }

        $decoded = json_decode($stdout, true);

        if (! is_array($decoded)) {
            Log::error('Keluaran engine Python bukan JSON', compact('command', 'stdout', 'stderr'));

            throw new PythonEngineException(
                "Engine mengembalikan keluaran yang tidak dapat dibaca untuk '{$command}'.",
            );
        }

        if (($decoded['ok'] ?? false) !== true) {
            throw new PythonEngineException(
                $decoded['error'] ?? "Analisis '{$command}' gagal tanpa keterangan.",
            );
        }

        // stderr yang tidak fatal (peringatan konvergensi sklearn/statsmodels)
        // dicatat saja; hasilnya tetap sah dan tidak perlu mengagalkan permintaan.
        if ($stderr !== '') {
            Log::info('Peringatan engine Python', compact('command', 'stderr'));
        }

        return [
            'data' => $decoded['data'] ?? [],
            'duration_ms' => $durationMs,
        ];
    }

    /*
     * Variabel lingkungan yang wajib ada bagi proses Python di Windows.
     *
     * `php artisan serve` hanya meneruskan sebagian kecil variabel ke server
     * bawaan PHP, sehingga SystemRoot ikut hilang. Tanpa SystemRoot, Winsock
     * gagal diinisialisasi dan setiap impor scikit-learn (lewat joblib) berhenti
     * dengan "WinError 10106" — padahal perintah yang sama berjalan normal dari
     * baris perintah. Nilainya dikembalikan di sini agar engine berperilaku sama
     * di kedua jalur.
     */
    private function essentialEnvironment(): array
    {
        if (PHP_OS_FAMILY !== 'Windows') {
            return [];
        }

        $temp = sys_get_temp_dir();

        return array_filter([
            'SystemRoot' => getenv('SystemRoot') ?: ($_SERVER['SystemRoot'] ?? 'C:\\Windows'),
            'windir' => getenv('windir') ?: ($_SERVER['windir'] ?? 'C:\\Windows'),
            'TEMP' => getenv('TEMP') ?: $temp,
            'TMP' => getenv('TMP') ?: $temp,
        ]);
    }

    private function assertRunnable(): void
    {
        if (! is_file($this->bin)) {
            throw new PythonEngineException(
                "Interpreter Python tidak ditemukan di {$this->bin}. ".
                'Periksa PYTHON_BIN pada berkas .env.',
            );
        }

        if (! is_file($this->entry)) {
            throw new PythonEngineException(
                "Skrip engine tidak ditemukan di {$this->entry}. ".
                'Periksa PYTHON_ENTRY pada berkas .env.',
            );
        }
    }

    /*
     * Traceback Python tidak berguna bagi pengguna aplikasi. Baris terakhirnya
     * justru yang paling informatif ("ModuleNotFoundError: ..."), jadi itu yang
     * ditampilkan; tracebacknya sendiri sudah masuk log.
     */
    private function readableFailure(string $command, string $stderr, ?int $exitCode): string
    {
        $lines = array_values(array_filter(explode("\n", $stderr), static fn ($line) => trim($line) !== ''));
        $last = trim((string) end($lines));

        if ($last === '') {
            return "Analisis '{$command}' berhenti dengan kode {$exitCode}.";
        }

        return "Analisis '{$command}' gagal: {$last}";
    }
}
