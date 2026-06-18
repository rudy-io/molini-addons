/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Production / énergie
        solar: '#1d9e75',
        'solar-dim': '#0f6e56',
        low: '#ba7517',
        // Surfaces Moli (dark-first — aligné thème chantier F au polish)
        moli: {
          bg: '#0f1115',
          surface: '#171a21',
          surface2: '#1f242e',
          border: '#2a313d',
          text: '#e6e9ef',
          muted: '#9aa3b2',
        },
      },
    },
  },
  plugins: [],
};
