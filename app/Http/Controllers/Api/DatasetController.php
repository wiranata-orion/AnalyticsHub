<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Services\DatasetService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

class DatasetController extends Controller
{
    public function __construct(private readonly DatasetService $datasets)
    {
    }

    public function index(): JsonResponse
    {
        $disk = Storage::disk(config('python.dataset_disk'));
        $files = $disk->files('datasets');
        $datasetList = [];

        foreach ($files as $file) {
            // Hanya baca file database mini (.json)
            if (pathinfo($file, PATHINFO_EXTENSION) === 'json') {
                $metadata = json_decode($disk->get($file), true);
                
                if ($metadata) {
                    $datasetList[] = [
                        'id'         => $metadata['id'],
                        'name'       => $metadata['name'],
                        'format'     => $metadata['format'],
                        'rows'       => $metadata['rows'],
                        'columns'    => $metadata['columns_count'] ?? 0,
                        'size'       => $metadata['size'],
                        'status'     => $metadata['status'],
                        'created_at' => $metadata['created_at'],
                        'updated_at' => null,
                    ];
                }
            }
        }

        // Urutkan dataset terbaru di atas
        usort($datasetList, fn($a, $b) => strtotime($b['created_at']) <=> strtotime($a['created_at']));

        return response()->json(['data' => $datasetList]);
    }

    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'file' => ['required', 'file', 'mimes:csv,txt,xlsx,xls', 'max:204800'],
            'delimiter' => ['nullable', 'string', 'max:8'],
            'encoding' => ['nullable', 'string', 'max:32'],
            'has_header' => ['nullable', 'boolean'],
        ]);

        $result = $this->datasets->store($request->file('file'), [
            'delimiter' => $validated['delimiter'] ?? ',',
            'encoding' => $validated['encoding'] ?? 'UTF-8',
            'has_header' => $request->boolean('has_header', true),
        ]);

        $profile = $result['profile'];
        
        // PERBAIKAN 1: ID sekarang murni nama filenya saja (tanpa awalan datasets/)
        $filename = basename($result['file_path']); 

        $formattedData = [
            'id'            => $filename,
            'name'          => $result['original_name'],
            'original_name' => $result['original_name'],
            'format'        => $result['format'],
            'delimiter'     => $validated['delimiter'] ?? ',',
            'encoding'      => $validated['encoding'] ?? 'UTF-8',
            'rows'          => $profile['row_count'] ?? 0,
            'columns_count' => $profile['column_count'] ?? 0,
            'size'          => $this->humanSize($result['size_bytes']),
            'status'        => 'ready',
            'error_message' => null,
            'created_at'    => now()->format('d M Y'),
            'columns'       => collect($profile['columns'] ?? [])->map(fn ($column) => [
                'name'          => $column['name'],
                'type'          => $column['type'],
                'missing'       => (float) ($column['missing_percent'] ?? 0),
                'missing_count' => $column['missing_count'] ?? 0,
                'unique'        => $column['unique_count'] ?? 0,
                'mean'          => $column['mean'] ?? null,
                'std'           => $column['std'] ?? null,
                'min'           => $column['min'] ?? null,
                'q1'            => $column['q1'] ?? null,
                'median'        => $column['median'] ?? null,
                'q3'            => $column['q3'] ?? null,
                'max'           => $column['max'] ?? null,
                'skewness'      => $column['skewness'] ?? null,
                'kurtosis'      => $column['kurtosis'] ?? null,
                'outlier_count' => $column['outlier_count'] ?? 0,
                'is_identifier' => $column['is_identifier'] ?? false,
                'top_values'    => $column['top_values'] ?? null,
            ])->toArray(),
        ];

        $disk = Storage::disk(config('python.dataset_disk'));
        // Simpan file JSON-nya
        $disk->put('datasets/' . $filename . '.json', json_encode($formattedData));

        return response()->json(['data' => $formattedData], 201);
    }

    // PERBAIKAN 2: Ubah dari Dataset $dataset menjadi string $id
    public function show(string $id): JsonResponse
    {
        $disk = Storage::disk(config('python.dataset_disk'));
        $jsonPath = 'datasets/' . $id . '.json';

        if (!$disk->exists($jsonPath)) {
            return response()->json(['message' => 'Dataset tidak ditemukan.'], 404);
        }

        // Baca langsung JSON-nya untuk merender halaman detail
        $metadata = json_decode($disk->get($jsonPath), true);
        return response()->json(['data' => $metadata]);
    }

    public function reprofile(string $id): JsonResponse
    {
        return $this->show($id); // Reprofile disamakan saja agar tidak error
    }

    // PERBAIKAN 3: Fitur Hapus membaca langsung dari file fisik, bukan database
    public function destroy(string $id): JsonResponse
    {
        $disk = Storage::disk(config('python.dataset_disk'));
        
        // 1. Keamanan: Ambil nama filenya saja untuk mencegah direktori traversal
        $filename = basename($id); 
        
        $filePath = 'datasets/' . $filename;
        $jsonPath = 'datasets/' . $filename . '.json';

        // 2. Pengecekan: Pastikan file dataset-nya memang ada di server
        if (!$disk->exists($jsonPath)) {
            return response()->json(['message' => 'Dataset tidak ditemukan atau sudah dihapus sebelumnya.'], 404);
        }

        // 3. Eksekusi: Hapus file aslinya dan file JSON pendampingnya
        $disk->delete($filePath);
        $disk->delete($jsonPath);
     
        return response()->json(['message' => 'Dataset berhasil dihapus.']);
    }

    private function humanSize(int $bytes): string
    {
        if ($bytes >= 1_048_576) {
            return number_format($bytes / 1_048_576, 1, ',', '.').' MB';
        }

        return number_format($bytes / 1024, 0, ',', '.').' KB';
    }
}