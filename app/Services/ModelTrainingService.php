<?php

namespace App\Services;

use App\Models\AnalysisRun;
use App\Models\Dataset;
use App\Models\FeatureSet;
use App\Models\TrainedModel;
use App\Exceptions\PythonEngineException;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

/*
 * Pelatihan model, AutoML, prediksi, dan penjelasan model (XAI).
 *
 * Model yang dilatih disimpan sebagai artefak di storage sehingga bisa dipakai
 * kembali untuk memprediksi dataset lain tanpa melatih ulang — itulah yang
 * membedakan "Saved Models" dari sekadar menampilkan hasil sekali jalan.
 *
 * Feature set diperlakukan sebagai sumber data alternatif: bila dipilih, model
 * dilatih dari berkas hasil Feature Engineering, bukan dari dataset mentah.
 */
class ModelTrainingService
{
    public function __construct(
        private readonly PythonEngine $engine,
        private readonly DatasetService $datasets,
    ) {
    }

    /** Sumber baris: feature set bila dipilih, selain itu dataset aslinya. */
    private function source(Dataset $dataset, ?FeatureSet $featureSet): array
    {
        if ($featureSet) {
            return [
                'path' => $featureSet->absolutePath(),
                'delimiter' => ',',
                'encoding' => 'UTF-8',
                'has_header' => true,
            ];
        }

        return $this->datasets->engineParams($dataset);
    }

    /*
     * Lokasi artefak selalu diturunkan dari disk Storage, bukan dari
     * storage_path() langsung: sejak Laravel 11 root disk `local` adalah
     * storage/app/private, sehingga menulis lewat storage_path('app/...') dan
     * membacanya lewat Storage::path() akan menunjuk dua folder berbeda.
     *
     * @return array{relative: string, absolute: string}
     */
    private function artifactPath(): array
    {
        $relative = 'models/'.Str::uuid().'.pkl';

        return [
            'relative' => $relative,
            'absolute' => Storage::disk(config('python.dataset_disk'))->path($relative),
        ];
    }

    public function train(Dataset $dataset, array $input): TrainedModel
    {
        $featureSet = $this->resolveFeatureSet($dataset, $input);
        $artifact = $this->artifactPath();

        $params = array_merge($this->source($dataset, $featureSet), [
            'target' => $input['target'],
            'features' => $input['features'],
            'algorithm' => $input['algorithm'] ?? null,
            'test_size' => $input['test_size'] ?? 0.2,
            'artifact_path' => $artifact['absolute'],
        ]);

        $model = TrainedModel::create([
            'dataset_id' => $dataset->id,
            'feature_set_id' => $featureSet?->id,
            'name' => $input['name'] ?? "Model {$input['target']}",
            'task' => 'classification',
            'algorithm' => $input['algorithm'] ?? 'random_forest',
            'target' => $input['target'],
            'features' => $input['features'],
            'params' => ['test_size' => $input['test_size'] ?? 0.2],
            'status' => 'training',
        ]);

        try {
            $result = $this->engine->run('ml.train', $params)['data'];
        } catch (\Throwable $error) {
            $model->update(['status' => 'failed', 'error_message' => $error->getMessage()]);

            throw $error;
        }

        $model->update([
            'task' => $result['task'],
            'algorithm' => $result['algorithm'],
            'features' => $result['features'],
            'metrics' => $result['metrics'],
            'evaluation' => json_encode($result, JSON_UNESCAPED_UNICODE),
            'artifact_path' => $artifact['relative'],
            'training_time_ms' => $result['training_time_ms'],
            'prediction_time_ms' => $result['prediction_time_ms'],
            'status' => 'ready',
        ]);

        return $model->fresh();
    }

    /**
     * AutoML: melatih beberapa algoritma sekaligus.
     *
     * Setiap algoritma dicatat sebagai TrainedModel tersendiri supaya halaman
     * Model Comparison bisa membandingkannya seperti model biasa, dan pengguna
     * bisa memakai model mana pun — bukan hanya yang menang.
     */
    public function autoMl(Dataset $dataset, array $input): array
    {
        $featureSet = $this->resolveFeatureSet($dataset, $input);
        $artifact = $this->artifactPath();

        $params = array_merge($this->source($dataset, $featureSet), [
            'target' => $input['target'],
            'features' => $input['features'],
            'algorithms' => $input['algorithms'] ?? null,
            'test_size' => $input['test_size'] ?? 0.2,
            'artifact_path' => $artifact['absolute'],
        ]);

        $run = AnalysisRun::create([
            'dataset_id' => $dataset->id,
            'kind' => 'automl',
            'variant' => $input['target'],
            'params' => ['target' => $input['target'], 'features' => $input['features']],
            'status' => 'running',
        ]);

        try {
            $outcome = $this->engine->run('ml.automl', $params);
        } catch (\Throwable $error) {
            $run->update(['status' => 'failed', 'error_message' => $error->getMessage()]);

            throw $error;
        }

        $result = $outcome['data'];

        $run->update([
            'result' => json_encode($result, JSON_UNESCAPED_UNICODE),
            'status' => 'ready',
            'duration_ms' => $outcome['duration_ms'],
        ]);

        $models = [];

        foreach ($result['results'] as $candidate) {
            if ($candidate['status'] !== 'ready') {
                continue;
            }

            $isBest = $candidate['algorithm'] === $result['best']['algorithm'];

            $models[] = TrainedModel::create([
                'dataset_id' => $dataset->id,
                'feature_set_id' => $featureSet?->id,
                'name' => $candidate['label'].' — '.$input['target'],
                'task' => $result['task'],
                'algorithm' => $candidate['algorithm'],
                'target' => $input['target'],
                'features' => $result['features'],
                'params' => ['automl' => true],
                'metrics' => $candidate['metrics'],
                'evaluation' => json_encode(
                    $isBest ? array_merge($candidate, $result['best']) : $candidate,
                    JSON_UNESCAPED_UNICODE,
                ),
                // Hanya pemenang yang artefaknya disimpan: menyimpan tujuh model
                // sekaligus memakan ruang tanpa ada yang memakainya.
                'artifact_path' => $isBest ? $artifact['relative'] : null,
                'training_time_ms' => $candidate['training_time_ms'],
                'prediction_time_ms' => $candidate['prediction_time_ms'],
                'is_best' => $isBest,
                'automl_run_id' => $run->id,
                'status' => 'ready',
            ]);
        }

        return ['run' => $run->fresh(), 'models' => $models];
    }

    public function predict(TrainedModel $model, Dataset $target): array
    {
        if (! $model->artifact_path) {
            throw new PythonEngineException(
                'Model ini tidak menyimpan artefak sehingga tidak bisa dipakai memprediksi. '
                .'Latih ulang model untuk menyimpannya.'
            );
        }

        return $this->engine->run('ml.predict', array_merge(
            $this->datasets->engineParams($target),
            ['artifact_path' => $model->absoluteArtifactPath()],
        ))['data'];
    }

    public function explain(TrainedModel $model, array $methods = []): array
    {
        if (! $model->artifact_path) {
            throw new PythonEngineException(
                'Model ini tidak menyimpan artefak sehingga belum bisa dijelaskan.'
            );
        }

        $source = $this->source($model->dataset, $model->featureSet);

        return $this->engine->run('ml.xai', array_merge($source, [
            'artifact_path' => $model->absoluteArtifactPath(),
            'methods' => $methods ?: ['feature_importance', 'shap', 'lime', 'decision_path'],
        ]))['data'];
    }

    private function resolveFeatureSet(Dataset $dataset, array $input): ?FeatureSet
    {
        if (empty($input['feature_set_id'])) {
            return null;
        }

        return $dataset->featureSets()->findOrFail($input['feature_set_id']);
    }

}
