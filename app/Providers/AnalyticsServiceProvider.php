<?php

namespace App\Providers;

use App\Services\PythonEngine;
use Illuminate\Support\ServiceProvider;

/*
 * PythonEngine dibangun dari konfigurasi dan dibagikan sebagai singleton:
 * kelasnya tidak menyimpan state antar panggilan, jadi tidak ada gunanya
 * membuat instance baru pada setiap injeksi.
 */
class AnalyticsServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->singleton(PythonEngine::class, fn () => PythonEngine::fromConfig());
    }
}
