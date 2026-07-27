<?php

use Illuminate\Support\Facades\Route;

/*
 * Frontend berdiri sendiri dan disajikan oleh Vite, jadi Laravel tidak lagi
 * merender halaman apa pun. Berkas ini sengaja dibiarkan kosong sampai REST API
 * dibuat — endpoint analitik nanti didaftarkan di `routes/api.php`.
 */

Route::get('/', fn () => response()->json([
    'name' => 'AnalyticsHub API',
    'status' => 'belum ada endpoint',
]));
