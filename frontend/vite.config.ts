import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "node:path";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      // Desactivado en dev para no interferir con HMR; solo activo en build
      devOptions: { enabled: false },
      manifest: {
        name: "Registro Venta Micro",
        short_name: "RegVenta",
        description: "Registro de ventas offline-first",
        theme_color: "#ffffff",
        background_color: "#ffffff",
        display: "standalone",
        start_url: "/",
        scope: "/",
      },
      workbox: {
        // Pre-cachea el app shell completo (JS, CSS, HTML)
        globPatterns: ["**/*.{js,css,html}"],
        runtimeCaching: [
          {
            // Catálogo: NetworkFirst con fallback a caché → soporta offline
            urlPattern: /\/api\/v1\/catalog/,
            handler: "NetworkFirst",
            options: {
              cacheName: "catalog-api-cache",
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24, // 24 h
              },
              networkTimeoutSeconds: 10,
            },
          },
        ],
      },
    }),
  ],
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
          if (
            id.includes("node_modules/react/") ||
            id.includes("node_modules/react-dom/") ||
            id.includes("node_modules/scheduler/")
          ) {
            return "react-vendor";
          }
          if (id.includes("node_modules/react-router")) {
            return "router-vendor";
          }
          if (id.includes("node_modules/@tanstack/react-query")) {
            return "query-vendor";
          }
          if (id.includes("node_modules/dexie")) {
            return "dexie-vendor";
          }
          return undefined;
        },
      },
    },
  },
});
