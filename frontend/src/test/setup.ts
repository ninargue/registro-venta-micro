import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./mocks/server";

// Inicia el servidor mock de MSW antes de toda la suite
beforeAll(() => {
  server.listen({ onUnhandledFrame: "error" });
});

// Restaura los handlers a su configuración inicial entre tests
afterEach(() => {
  server.resetHandlers();
});

// Limpia el servidor al finalizar los tests
afterAll(() => {
  server.close();
});
