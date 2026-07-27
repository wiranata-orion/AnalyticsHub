/*
 * Registrasi Chart.js dilakukan di sini, bukan di `app.js`, supaya halaman yang
 * tidak menampilkan chart tidak ikut memuat Chart.js. Modul ES dievaluasi sekali
 * per bundle, jadi pemanggilan berulang dari beberapa komponen tetap aman.
 */
import {
    ArcElement,
    BarController,
    BarElement,
    CategoryScale,
    Chart,
    DoughnutController,
    Filler,
    LineController,
    LineElement,
    LinearScale,
    PointElement,
    ScatterController,
    Tooltip,
} from 'chart.js';

Chart.register(
    ArcElement,
    BarController,
    BarElement,
    CategoryScale,
    DoughnutController,
    Filler,
    LineController,
    LineElement,
    LinearScale,
    PointElement,
    ScatterController,
    Tooltip,
);

/*
 * Plugin `Legend` sengaja TIDAK didaftarkan: identitas seri dibawa komponen
 * ChartLegend sendiri agar gaya dan urutan swatch konsisten dengan sisa
 * antarmuka. Karena tidak terdaftar, `Chart.defaults.plugins.legend` juga tidak
 * ada — jangan menyentuhnya di sini, itu akan melempar TypeError saat impor.
 */
Chart.defaults.font.family =
    'Figtree, system-ui, -apple-system, "Segoe UI", sans-serif';
Chart.defaults.maintainAspectRatio = false;

export { Chart };
