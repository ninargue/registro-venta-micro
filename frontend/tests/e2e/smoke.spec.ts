import { expect, test } from "@playwright/test";

test('la ruta "/" muestra el h1 con el nombre del producto', async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("registro-venta-micro");
});
