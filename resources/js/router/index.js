import { createRouter, createWebHistory } from 'vue-router';

/*
 * Seluruh halaman dimuat malas (lazy) agar tiap rute jadi chunk terpisah —
 * halaman tanpa chart tidak ikut menarik Chart.js.
 *
 * `name` dipakai komponen navigasi lewat `:to="{ name: '...' }"`, jadi mengubah
 * `path` tidak akan merusak tautan di sidebar.
 */
const routes = [
    {
        path: '/',
        redirect: { name: 'dashboard' },
    },
    {
        path: '/dashboard',
        name: 'dashboard',
        component: () => import('@/Pages/Dashboard.vue'),
        meta: { title: 'Dashboard' },
    },
    {
        path: '/datasets',
        name: 'datasets.index',
        component: () => import('@/Pages/Datasets/Index.vue'),
        meta: { title: 'Dataset' },
    },
    {
        path: '/datasets/create',
        name: 'datasets.create',
        component: () => import('@/Pages/Datasets/Create.vue'),
        meta: { title: 'Upload Dataset' },
    },
    {
        // Ditaruh setelah `/datasets/create` supaya "create" tidak tertangkap
        // sebagai id dataset.
        path: '/datasets/:id',
        name: 'datasets.show',
        component: () => import('@/Pages/Datasets/Show.vue'),
        props: true,
        meta: { title: 'Detail Dataset' },
    },
    {
        path: '/profiling',
        name: 'profiling.index',
        component: () => import('@/Pages/Profiling/Index.vue'),
        meta: { title: 'Data Profiling' },
    },
    {
        path: '/cleaning',
        name: 'cleaning.index',
        component: () => import('@/Pages/Cleaning/Index.vue'),
        meta: { title: 'Data Cleaning' },
    },
    {
        path: '/visualization',
        name: 'visualization.index',
        component: () => import('@/Pages/Visualization/Index.vue'),
        meta: { title: 'Visualisasi' },
    },
    {
        path: '/eda',
        name: 'eda.index',
        component: () => import('@/Pages/Eda/Index.vue'),
        meta: { title: 'Exploratory Data Analysis' },
    },
    {
        path: '/statistical-analysis',
        name: 'statistical-analysis.index',
        component: () => import('@/Pages/Statistics/Index.vue'),
        meta: { title: 'Analisis Statistik' },
    },
    {
        path: '/data-quality',
        name: 'data-quality.index',
        component: () => import('@/Pages/Quality/Index.vue'),
        meta: { title: 'Data Quality' },
    },
    {
        path: '/auto-recommendation',
        name: 'auto-recommendation.index',
        component: () => import('@/Pages/Recommendation/Index.vue'),
        meta: { title: 'Auto Recommendation' },
    },
    {
        path: '/feature-engineering',
        name: 'feature-engineering.index',
        component: () => import('@/Pages/FeatureEngineering/Index.vue'),
        meta: { title: 'Feature Engineering' },
    },
    {
        path: '/automl',
        name: 'automl.index',
        component: () => import('@/Pages/AutoMl/Index.vue'),
        meta: { title: 'AutoML' },
    },
    {
        path: '/model-comparison',
        name: 'model-comparison.index',
        component: () => import('@/Pages/ModelComparison/Index.vue'),
        meta: { title: 'Model Comparison' },
    },
    {
        path: '/explainable-ai',
        name: 'explainable-ai.index',
        component: () => import('@/Pages/Xai/Index.vue'),
        meta: { title: 'Explainable AI' },
    },
    {
        path: '/forecasting',
        name: 'forecasting.index',
        component: () => import('@/Pages/Forecasting/Index.vue'),
        meta: { title: 'Forecasting' },
    },
    {
        path: '/auto-insight',
        name: 'auto-insight.index',
        component: () => import('@/Pages/Insight/Index.vue'),
        meta: { title: 'Auto Insight' },
    },
    {
        path: '/mining',
        name: 'mining.index',
        component: () => import('@/Pages/Mining/Index.vue'),
        meta: { title: 'Data Mining' },
    },
    {
        path: '/machine-learning',
        name: 'machine-learning.index',
        component: () => import('@/Pages/MachineLearning/Index.vue'),
        meta: { title: 'Machine Learning' },
    },
    {
        path: '/reports',
        name: 'reports.index',
        component: () => import('@/Pages/Reports/Index.vue'),
        meta: { title: 'Laporan' },
    },
    {
        path: '/settings',
        name: 'settings.index',
        component: () => import('@/Pages/Settings/Index.vue'),
        meta: { title: 'Pengaturan' },
    },
    {
        path: '/:pathMatch(.*)*',
        name: 'not-found',
        component: () => import('@/Pages/NotFound.vue'),
        meta: { title: 'Halaman Tidak Ditemukan' },
    },
];

const router = createRouter({
    history: createWebHistory(),
    routes,
    scrollBehavior: () => ({ top: 0 }),
});

router.afterEach((to) => {
    document.title = to.meta.title
        ? `${to.meta.title}`
        : 'AnalyticsHub';
});

export default router;
