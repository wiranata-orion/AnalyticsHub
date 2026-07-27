import defaultTheme from 'tailwindcss/defaultTheme';
import forms from '@tailwindcss/forms';

/** @type {import('tailwindcss').Config} */
export default {
    darkMode: 'class',

    content: [
        './vendor/laravel/framework/src/Illuminate/Pagination/resources/views/*.blade.php',
        './storage/framework/views/*.php',
        './resources/views/**/*.blade.php',
        './resources/js/**/*.vue',
    ],

    theme: {
        extend: {
            fontFamily: {
                sans: ['Figtree', ...defaultTheme.fontFamily.sans],
            },

            /*
             * Token warna AnalyticsHub.
             *
             * Setiap peran punya pasangan terang/gelap dengan sufiks `-dark`,
             * dipakai lewat pola `bg-surface dark:bg-surface-dark`. Nilai seri
             * dan status sudah lolos validasi colorblind-safe pada kedua
             * permukaan, jadi jangan diubah sebagian — ganti satu set penuh.
             */
            colors: {
                // Permukaan
                plane: '#f9f9f7',
                'plane-dark': '#0d0d0d',
                surface: '#fcfcfb',
                'surface-dark': '#1a1a19',
                raised: '#ffffff',
                'raised-dark': '#242422',

                // Garis
                hairline: '#e1e0d9',
                'hairline-dark': '#2c2c2a',
                baseline: '#c3c2b7',
                'baseline-dark': '#383835',

                // Teks
                ink: '#0b0b0b',
                'ink-dark': '#ffffff',
                'ink-2': '#52514e',
                'ink-2-dark': '#c3c2b7',
                'ink-3': '#898781',
                'ink-3-dark': '#898781',

                // Aksen (mengikuti slot seri 1)
                accent: '#2a78d6',
                'accent-dark': '#3987e5',

                // Palet kategorikal — urutan slot adalah mekanisme keamanan
                // colorblind, bukan kosmetik. Pakai berurutan, jangan diputar.
                series: {
                    1: '#2a78d6',
                    2: '#eb6834',
                    3: '#1baf7a',
                    4: '#eda100',
                    5: '#e87ba4',
                    6: '#008300',
                    7: '#4a3aa7',
                    8: '#e34948',
                },
                'series-dark': {
                    1: '#3987e5',
                    2: '#d95926',
                    3: '#199e70',
                    4: '#c98500',
                    5: '#d55181',
                    6: '#008300',
                    7: '#9085e9',
                    8: '#e66767',
                },

                // Status — tidak pernah dipakai sebagai warna seri
                status: {
                    good: '#0ca30c',
                    warning: '#fab219',
                    serious: '#ec835a',
                    critical: '#d03b3b',
                },
            },
        },
    },

    plugins: [forms],
};
