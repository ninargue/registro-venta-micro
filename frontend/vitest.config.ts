import { configDefaults, defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config.ts";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      include: ["src/**/*.test.{ts,tsx}"],
      // Los specs de Playwright viven en tests/e2e y no los ejecuta Vitest.
      exclude: [...configDefaults.exclude, "tests/e2e/**"],
    },
  }),
);
