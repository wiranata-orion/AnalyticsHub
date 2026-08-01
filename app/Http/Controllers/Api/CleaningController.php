<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Services\DatasetService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

class CleaningController extends Controller
{
    public function __construct(private readonly DatasetService $datasets)
    {
    }

    public function show(string $dataset): JsonResponse
    {
        try {
            return response()->json(['data' => $this->datasets->localCleaningPreview($dataset)]);
        } catch (\RuntimeException $error) {
            return response()->json(['message' => $error->getMessage()], 404);
        }
    }

    public function apply(Request $request, string $dataset): JsonResponse
    {
        $validated = $request->validate([
            'strategies' => ['nullable', 'array'],
        ]);

        try {
            return response()->json([
                'data' => $this->datasets->cleanLocal($dataset, $validated['strategies'] ?? []),
            ]);
        } catch (\RuntimeException $error) {
            return response()->json(['message' => $error->getMessage()], 404);
        }
    }

    public function download(string $dataset)
    {
        $disk = Storage::disk(config('python.dataset_disk'));
        $filename = basename($dataset);
        $relativePath = 'cleaning/'.$filename.'.csv';
        $path = $disk->path($relativePath);

        if (! $disk->exists($relativePath)) {
            return response()->json(['message' => 'Hasil cleaning belum tersedia.'], 404);
        }

        return response()->download($path, basename($path));
    }
}