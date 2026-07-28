<script setup>
import { computed } from 'vue'
import * as Icons from 'lucide-vue-next'

const props = defineProps({
    name: {
        type: String,
        required: true,
    },
})

const iconMap = {
    // Sidebar
    dashboard: Icons.LayoutDashboard,
    datasets: Icons.Database,
    profiling: Icons.ScanSearch,
    cleaning: Icons.Sparkles,

    visualization: Icons.ChartColumn,

    eda: Icons.Search,

    'statistical-analysis': Icons.Sigma,

    'data-quality': Icons.BadgeCheck,

    'auto-recommendation': Icons.Lightbulb,

    mining: Icons.Pickaxe,

    'feature-engineering': Icons.Wrench,

    ml: Icons.Brain,

    automl: Icons.Bot,

    'model-comparison': Icons.GitCompare,

    'explainable-ai': Icons.Eye,

    forecasting: Icons.TrendingUp,

    reports: Icons.FileText,

    'auto-insight': Icons.Sparkles,

    settings: Icons.Settings,

    // Kontrol tema — tiga status: terang, gelap, ikut sistem
    sun: Icons.Sun,
    moon: Icons.Moon,
    system: Icons.Monitor,

    // General
    upload: Icons.Upload,
    download: Icons.Download,
    play: Icons.Play,
    plus: Icons.Plus,
    trash: Icons.Trash2,
    pencil: Icons.Pencil,
    eye: Icons.Eye,
    refresh: Icons.RefreshCw,
    filter: Icons.Filter,
    search: Icons.Search,
    table: Icons.Table,
    document: Icons.File,
    bell: Icons.Bell,
    menu: Icons.Menu,
    close: Icons.X,
    chevronDown: Icons.ChevronDown,
    chevronRight: Icons.ChevronRight,
    check: Icons.Check,
    warning: Icons.TriangleAlert,
    trendUp: Icons.TrendingUp,
    trendDown: Icons.TrendingDown,
    logout: Icons.LogOut,
    user: Icons.User,
    sidebar: Icons.PanelLeft,
}

const icon = computed(() => iconMap[props.name] || Icons.CircleHelp)
</script>

<template>
    <!-- Ukuran tidak ditetapkan di sini: setiap pemanggil sudah mengirim kelas
         h-*/w-* sendiri, dan kelas bawaan akan bertabrakan dengannya. -->
    <component :is="icon" :stroke-width="1.8" />
</template>