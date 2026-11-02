import { defineConfig, devices } from "@playwright/test";

const PREVIEW_PORT = 4174;
const PREVIEW_URL = `http://localhost:${PREVIEW_PORT}`;

export default defineConfig({
  testDir: "tests/e2e",
  use: {
    baseURL: PREVIEW_URL,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    // Autosuficiente: compila y sirve el build con vite preview; sin pasos previos.
    command: "npm run build && npx vite preview",
    url: PREVIEW_URL,
    // Nunca reutilizar un servidor ajeno en este puerto: siempre arranca el propio.
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
