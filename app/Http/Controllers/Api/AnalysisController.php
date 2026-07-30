<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Dataset;
use App\Services\AnalysisService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/*
 * Seluruh analisis non-model: EDA, statistik, mining, kualitas data, insight,
 * rekomendasi, dan cleaning.
 *
 * Satu controller karena bentuk permintaannya identik — dataset + parameter,
 * lalu hasil JSON. Yang membedakan hanya perintah engine yang dipanggil, dan itu
 * dipetakan di satu tabel di bawah alih-alih tersebar sebagai belasan method
 * yang isinya sama.
 */
class AnalysisController extends Controller
{
    public function __construct(private readonly AnalysisService $analysis)
    {
    }

    /** variant => [kind, perintah engine, aturan validasi tambahan] */
    private const ROUTES = [
        // Exploratory Data Analysis
        'univariate' => ['eda', 'eda.univariate', ['column' => ['nullable', 'string']]],
        'bivariate' => ['eda', 'eda.bivariate', ['x' => ['required', 'string'], 'y' => ['required', 'string']]],
        'multivariate' => ['eda', 'eda.multivariate', ['columns' => ['nullable', 'array'], 'color' => ['nullable', 'string']]],
        'correlation' => ['eda', 'eda.correlation', ['method' => ['nullable', 'in:pearson,spearman,kendall'], 'columns' => ['nullable', 'array']]],
        'distribution' => ['eda', 'eda.distribution', ['columns' => ['nullable', 'array']]],
        'pairplot' => ['eda', 'eda.pairplot', ['columns' => ['nullable', 'array'], 'color' => ['nullable', 'string']]],
        'missing_pattern' => ['eda', 'eda.missing_pattern', []],
        'feature_relationship' => ['eda', 'eda.feature_relationship', ['target' => ['required', 'string']]],

        // Statistik
        'descriptive' => ['statistics', 'stats.descriptive', ['columns' => ['nullable', 'array']]],
        'inferential' => ['statistics', 'stats.inferential', [
            'test' => ['required', 'in:t_test,anova,mann_whitney,kruskal,chi_square,pearson,spearman'],
            'value' => ['nullable', 'string'],
            'group' => ['nullable', 'string'],
            'x' => ['nullable', 'string'],
            'y' => ['nullable', 'string'],
            'alpha' => ['nullable', 'numeric', 'between:0.001,0.2'],
        ]],

        // Data mining
        'clustering' => ['mining', 'mining.clustering', ['k' => ['nullable', 'integer', 'between:2,20'], 'algorithm' => ['nullable', 'in:kmeans,dbscan,hierarchical'], 'columns' => ['nullable', 'array']]],
        'classification' => ['mining', 'mining.classification', ['target' => ['nullable', 'string'], 'features' => ['nullable', 'array']]],
        'regression' => ['mining', 'mining.regression', ['target' => ['nullable', 'string'], 'features' => ['nullable', 'array']]],
        'association' => ['mining', 'mining.association', ['min_support' => ['nullable', 'numeric'], 'min_confidence' => ['nullable', 'numeric'], 'columns' => ['nullable', 'array']]],
        'anomaly' => ['mining', 'mining.anomaly', ['method' => ['nullable', 'in:isolation_forest,lof,iqr'], 'contamination' => ['nullable', 'numeric']]],
        'timeseries' => ['mining', 'mining.timeseries', ['time_column' => ['nullable', 'string'], 'value_column' => ['nullable', 'string'], 'freq' => ['nullable', 'string']]],

        // Lainnya
        'recommendation' => ['recommendation', 'recommendation.suggest', []],
        'insight' => ['insight', 'insight.generate', []],
        'quality' => ['quality', 'quality.assess', []],
        'forecasting' => ['forecasting', 'forecast.run', [
            'time_column' => ['nullable', 'string'],
            'value_column' => ['nullable', 'string'],
            'horizon' => ['nullable', 'integer', 'between:1,120'],
            'models' => ['nullable', 'array'],
        ]],
    ];

    public function run(Request $request, Dataset $dataset, string $variant): JsonResponse
    {
        $route = self::ROUTES[$variant] ?? null;

        if ($route === null) {
            return response()->json([
                'message' => "Analisis '{$variant}' tidak dikenal.",
                'available' => array_keys(self::ROUTES),
            ], 404);
        }

        [$kind, $command, $rules] = $route;

        $params = array_filter(
            $request->validate($rules),
            static fn ($value) => $value !== null,
        );

        $run = $this->analysis->run($dataset, $kind, $variant, $command, $params);

        return response()->json([
            'data' => $run->resultArray(),
            'meta' => [
                'run_id' => $run->id,
                'duration_ms' => $run->duration_ms,
                'ran_at' => $run->created_at?->toIso8601String(),
            ],
        ]);
    }

    /** Hasil terakhir tanpa menghitung ulang — dipakai saat halaman dibuka lagi. */
    public function latest(Dataset $dataset, string $variant): JsonResponse
    {
        $route = self::ROUTES[$variant] ?? null;

        if ($route === null) {
            return response()->json(['message' => "Analisis '{$variant}' tidak dikenal."], 404);
        }

        $run = $this->analysis->latest($dataset, $route[0], $variant);

        if (! $run) {
            return response()->json(['data' => null, 'meta' => null]);
        }

        return response()->json([
            'data' => $run->resultArray(),
            'meta' => [
                'run_id' => $run->id,
                'duration_ms' => $run->duration_ms,
                'ran_at' => $run->created_at?->toIso8601String(),
                'params' => $run->params,
            ],
        ]);
    }
}
