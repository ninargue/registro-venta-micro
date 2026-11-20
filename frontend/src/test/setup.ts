import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./mocks/server";

// Inicia el servidor mock de MSW antes de toda la suite con fallo ante requests no mockeadas
beforeAll(() => {
  server.listen({ onUnhandledFrame: "error" });
});

// Restaura handlers, DOM y almacenamiento entre tests para aislamiento total
afterEach(() => {
  cleanup();
  server.resetHandlers();
  localStorage.clear();
  sessionStorage.clear();
  document.documentElement.removeAttribute("class");
  document.documentElement.removeAttribute("data-theme");
});

// Limpia el servidor al finalizar los tests
afterAll(() => {
  server.close();
});
