<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Dataset;
use App\Models\FeatureSet;
use App\Services\FeatureEngineeringService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

class FeatureSetController extends Controller
{
    public function __construct(private readonly FeatureEngineeringService $features)
    {
    }

    public function index(Dataset $dataset): JsonResponse
    {
        return response()->json([
            'data' => $dataset->featureSets()->latest('id')->get()->map(fn ($set) => [
                'id' => $set->id,
                'name' => $set->name,
                'steps' => $set->steps,
                'columns' => $set->columns,
                'row_count' => $set->row_count,
                'column_count' => $set->column_count,
                'created_at' => $set->created_at?->format('d M Y H:i'),
            ]),
        ]);
    }

    public function store(Request $request, Dataset $dataset): JsonResponse
    {
        $validated = $request->validate([
            'name' => ['nullable', 'string', 'max:120'],
            'target' => ['nullable', 'string'],
            'steps' => ['required', 'array', 'min:1'],
            'steps.*.step' => [
                'required',
                'in:label_encoding,one_hot,standard_scaling,minmax_scaling,normalization,pca',
            ],
            'steps.*.columns' => ['nullable', 'array'],
            'steps.*.components' => ['nullable', 'integer', 'between:1,50'],
        ]);

        $set = $this->features->transform($dataset, $validated);

        return response()->json(['data' => [
            'id' => $set->id,
            'name' => $set->name,
            'steps' => $set->steps,
            'columns' => $set->columns,
            'row_count' => $set->row_count,
            'column_count' => $set->column_count,
        ]], 201);
    }

    public function selection(Request $request, Dataset $dataset): JsonResponse
    {
        $validated = $request->validate([
            'target' => ['required', 'string'],
            'top_k' => ['nullable', 'integer', 'between:1,50'],
        ]);

        return response()->json([
            'data' => $this->features->selection(
                $dataset,
                $validated['target'],
                $validated['top_k'] ?? 10,
            ),
        ]);
    }

    public function destroy(FeatureSet $featureSet): JsonResponse
    {
        Storage::disk(config('python.dataset_disk'))->delete($featureSet->path);
        $featureSet->delete();

        return response()->json(['message' => 'Feature set dihapus.']);
    }
}
