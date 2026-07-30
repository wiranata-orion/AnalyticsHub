<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Dataset;
use App\Models\TrainedModel;
use App\Services\ModelTrainingService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class ModelController extends Controller
{
    public function __construct(private readonly ModelTrainingService $training)
    {
    }

    public function index(Request $request): JsonResponse
    {
        $models = TrainedModel::with('dataset:id,name')
            ->when($request->integer('dataset_id'), fn ($query, $id) => $query->where('dataset_id', $id))
            ->latest('id')
            ->get();

        return response()->json(['data' => $models->map(fn ($model) => $this->summary($model))]);
    }

    public function store(Request $request, Dataset $dataset): JsonResponse
    {
        $validated = $request->validate([
            'name' => ['nullable', 'string', 'max:120'],
            'target' => ['required', 'string'],
            'features' => ['required', 'array', 'min:1'],
            'features.*' => ['string'],
            'algorithm' => ['nullable', 'string'],
            'feature_set_id' => ['nullable', 'integer'],
            'test_size' => ['nullable', 'numeric', 'between:0.1,0.5'],
        ]);

        $model = $this->training->train($dataset, $validated);

        return response()->json(['data' => $this->detail($model)], 201);
    }

    public function autoMl(Request $request, Dataset $dataset): JsonResponse
    {
        $validated = $request->validate([
            'target' => ['required', 'string'],
            'features' => ['required', 'array', 'min:1'],
            'features.*' => ['string'],
            'algorithms' => ['nullable', 'array'],
            'feature_set_id' => ['nullable', 'integer'],
            'test_size' => ['nullable', 'numeric', 'between:0.1,0.5'],
        ]);

        $outcome = $this->training->autoMl($dataset, $validated);

        return response()->json([
            'data' => $outcome['run']->resultArray(),
            'models' => collect($outcome['models'])->map(fn ($model) => $this->summary($model)),
            'meta' => ['run_id' => $outcome['run']->id, 'duration_ms' => $outcome['run']->duration_ms],
        ], 201);
    }

    public function show(TrainedModel $model): JsonResponse
    {
        return response()->json(['data' => $this->detail($model)]);
    }

    public function predict(Request $request, TrainedModel $model): JsonResponse
    {
        $validated = $request->validate(['dataset_id' => ['required', 'integer']]);
        $target = Dataset::findOrFail($validated['dataset_id']);

        return response()->json([
            'data' => $this->training->predict($model, $target),
            'meta' => ['model' => $model->name, 'dataset' => $target->name],
        ]);
    }

    public function explain(Request $request, TrainedModel $model): JsonResponse
    {
        $validated = $request->validate([
            'methods' => ['nullable', 'array'],
            'methods.*' => ['in:feature_importance,shap,lime,decision_path'],
        ]);

        return response()->json([
            'data' => $this->training->explain($model, $validated['methods'] ?? []),
        ]);
    }

    public function destroy(TrainedModel $model): JsonResponse
    {
        if ($model->artifact_path) {
            \Illuminate\Support\Facades\Storage::disk(config('python.dataset_disk'))
                ->delete($model->artifact_path);
        }

        $model->delete();

        return response()->json(['message' => 'Model dihapus.']);
    }

    private function summary(TrainedModel $model): array
    {
        $headline = $model->headlineMetric();

        return [
            'id' => $model->id,
            'name' => $model->name,
            'dataset_id' => $model->dataset_id,
            'dataset_name' => $model->dataset?->name,
            'task' => $model->task,
            'algorithm' => $model->algorithm,
            'target' => $model->target,
            'features' => $model->features,
            'metrics' => $model->metrics,
            'metric_label' => $headline['label'],
            'metric_value' => $headline['value'],
            'training_time_ms' => $model->training_time_ms,
            'prediction_time_ms' => $model->prediction_time_ms,
            'is_best' => $model->is_best,
            'has_artifact' => (bool) $model->artifact_path,
            'status' => $model->status,
            'trained_at' => $model->created_at?->format('d M Y H:i'),
        ];
    }

    private function detail(TrainedModel $model): array
    {
        return array_merge($this->summary($model), [
            'evaluation' => $model->evaluationArray(),
        ]);
    }
}
