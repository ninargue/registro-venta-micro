import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve(import.meta.dirname, "src"),
    },
  },
  server: {
    // Puerto propio y fijo; strictPort hace que Vite falle si está ocupado en vez de cambiarlo.
    port: 5174,
    strictPort: true,
    proxy: {
      // En producción la PWA y la API comparten dominio; en dev el proxy reenvía /api al backend.
      "/api": "http://localhost:8000",
    },
  },
  preview: {
    // Puerto propio y fijo para `vite preview` (lo usa el webServer de Playwright).
    port: 4174,
    strictPort: true,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            return "vendor";
          }
          return undefined;
        },
      },
    },
  },
});
