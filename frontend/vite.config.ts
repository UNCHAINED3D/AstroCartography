import { defineConfig } from 'vite';

// Build the frontend as a static bundle the FastAPI backend can serve directly
// (no dev server in production). Relative base so assets resolve no matter what
// path prefix the backend mounts them under.
export default defineConfig({
  base: './',
  build: {
    // Cesium's ESM build uses modern syntax (incl. top-level await), so target
    // a contemporary ES level rather than es2020.
    target: 'es2022',
    cssCodeSplit: true,
    reportCompressedSize: true,
    rollupOptions: {
      output: {
        // Split the heavy Cesium renderer into its own long-lived chunk so the
        // app shell can be cached independently of the globe engine.
        manualChunks(id: string) {
          if (id.includes('node_modules/cesium')) return 'cesium';
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
});
