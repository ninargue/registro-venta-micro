import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

// Vitest no procesa el CSS (`?raw` devuelve ""), por eso se lee el archivo directamente.
const indexCss = readFileSync(resolve(import.meta.dirname, "../../index.css"), "utf-8");

/**
 * jsdom no evalúa Tailwind, así que se verifica la configuración que hace que el botón
 * de tema (que solo escribe `data-theme` en <html>) controle realmente los estilos.
 */
describe("Tema claro/oscuro controlado por data-theme", () => {
  it("lee el contenido real de index.css", () => {
    expect(indexCss).toContain("@import");
  });

  it("la variante `dark:` de Tailwind sigue a data-theme y no al sistema operativo", () => {
    expect(indexCss).toMatch(
      /@custom-variant\s+dark\s*\(\s*&:where\(\s*\[data-theme="dark"\]\s*,\s*\[data-theme="dark"\]\s+\*\s*\)\s*\)\s*;/,
    );
  });

  it("el fondo y el texto del body cambian con data-theme", () => {
    expect(indexCss).toMatch(/\[data-theme="dark"\]\s+body\s*\{/);
  });

  it("no depende de una clase .dark que nadie aplica al documento", () => {
    expect(indexCss).not.toMatch(/\.dark\s+body/);
  });
});
