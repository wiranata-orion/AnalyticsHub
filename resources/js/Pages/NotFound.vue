<script setup>
import EmptyState from '@/Components/UI/EmptyState.vue';
import AppButton from '@/Components/UI/AppButton.vue';
import AppCard from '@/Components/UI/AppCard.vue';
</script>

<template>
    <AppCard flush>
        <EmptyState
            icon="search"
            title="Halaman tidak ditemukan"
            description="Alamat yang Anda buka tidak tersedia atau sudah dipindahkan."
        >
            <template #action>
                <AppButton
                    variant="primary"
                    icon="dashboard"
                    :to="{ name: 'dashboard' }"
                >
                    Kembali ke Dashboard
                </AppButton>
            </template>
        </EmptyState>
    </AppCard>
</template>
