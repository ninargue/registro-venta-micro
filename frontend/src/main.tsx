import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";
import { registerSW } from "virtual:pwa-register";

import { Providers } from "@/app/providers";
import { router } from "@/app/router";
import "./index.css";

// Registra el Service Worker generado por VitePWA/Workbox.
// En modo autoUpdate el SW se instala y actualiza silenciosamente.
registerSW({ immediate: true });

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("No se encontró el elemento #root");
}

createRoot(rootElement).render(
  <StrictMode>
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  </StrictMode>,
);
