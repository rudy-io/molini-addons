import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';

// Two modes:
//  - default (dev/preview): serves index.html → src/dev/main.tsx with a mock hass.
//  - `--mode lib` (prod): builds a single-file custom-element bundle moli-panel.js
//    (CSS inlined) that HA loads via panel_custom from /local/moli/.
export default defineConfig(({ mode }) => ({
  plugins: [preact()],
  build:
    mode === 'lib'
      ? {
          lib: {
            entry: 'src/element.ts',
            formats: ['es'],
            fileName: () => 'moli-panel.js',
          },
          cssCodeSplit: false,
          rollupOptions: { output: { inlineDynamicImports: true } },
          outDir: 'dist',
          emptyOutDir: true,
        }
      : { outDir: 'dist-dev' },
  test: { environment: 'jsdom', globals: true },
}));
