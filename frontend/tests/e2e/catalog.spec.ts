/**
 * catalog.spec.ts — E2E camino crítico: Crear producto y verificar en lista
 *
 * Escenario R-15 (spec.md):
 * GIVEN  un usuario dueño autenticado en la PWA
 * WHEN   navega a "Catálogo", activa "Agregar producto",
 *        completa nombre "Yerba Mate 1kg" y precio "3500.50", confirma el formulario
 * THEN   es redirigido al catálogo y el producto "Yerba Mate 1kg" aparece visible
 *        en la lista con precio "3500.50"
 *
 * Uses page.route to control API responses; unique test data per run via
 * TEST_RUN_ID suffix prevents cross-run pollution.
 */

import { expect, test } from "@playwright/test";

const TEST_RUN_ID = Date.now().toString(36);

test("R-15: camino crítico — login → /catalog → agregar producto → verificar en lista", async ({
  page,
}) => {
  const productName = `Yerba Mate 1kg ${TEST_RUN_ID}`;
  const productPrice = "3500.50";
  const productId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

  let productCreated = false;

  const user = {
    id: "11111111-1111-4111-8111-111111111111",
    email: "dueno@negocio.com",
  };

  const business = {
    id: "22222222-2222-4222-8222-222222222222",
    name: "Kiosco Central",
    country: "AR",
    timezone: "America/Argentina/Buenos_Aires",
    role: "owner" as const,
  };

  // ── Mock auth endpoints ────────────────────────────────────────────────────

  await page.route("**/api/v1/auth/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (url.pathname === "/api/v1/auth/me" && request.method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user,
          requires_onboarding: false,
          business,
        }),
      });
      return;
    }

    if (url.pathname === "/api/v1/auth/login" && request.method() === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user,
          requires_onboarding: false,
          business,
        }),
      });
      return;
    }

    if (url.pathname === "/api/v1/auth/refresh" && request.method() === "POST") {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({
          code: "UNAUTHENTICATED",
          message: "Sesión expirada",
          details: null,
        }),
      });
      return;
    }

    await route.fallback();
  });

  // ── Mock catalog endpoints ────────────────────────────────────────────────

  await page.route("**/api/v1/catalog/products**", async (route) => {
    const request = route.request();

    if (request.method() === "GET") {
      const items = productCreated
        ? [
            {
              id: productId,
              code: null,
              name: productName,
              sale_price: productPrice,
              cost_price: null,
              stock: "0.00",
              is_active: true,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          ]
        : [];

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items,
          total: items.length,
          limit: 50,
          offset: 0,
        }),
      });
      return;
    }

    if (request.method() === "POST") {
      const body = request.postDataJSON() as Record<string, unknown>;
      productCreated = true;
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: productId,
          code: null,
          name: body.name as string,
          sale_price: String(body.sale_price),
          cost_price: null,
          stock: "0.00",
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }),
      });
      return;
    }

    await route.fallback();
  });

  // ── 1. Navigate to /login (or / which redirects if unauthenticated) ───────

  await page.goto("/login");
  await expect(page).toHaveURL(/\/login$/);

  // ── 2. Perform login ──────────────────────────────────────────────────────

  await page.getByLabel(/Correo electrónico/i).fill(user.email);
  await page.getByLabel(/Contraseña/i).fill("ClaveSegura123");
  await page.getByRole("button", { name: "Iniciar Sesión" }).click();

  // After login, should be at /
  await expect(page).toHaveURL(/\/$/, { timeout: 10_000 });

  // ── 3. Navigate to /catalog ───────────────────────────────────────────────

  await page.goto("/catalog");
  await expect(page).toHaveURL(/\/catalog$/);
  await expect(page.getByRole("heading", { name: /Catálogo de productos/i })).toBeVisible();

  // ── 4. Activate "Agregar producto" ────────────────────────────────────────

  await page.getByRole("button", { name: /agregar producto|nuevo producto/i }).click();
  await expect(page).toHaveURL(/\/catalog\/new$/);

  // ── 5. Fill in the create form ────────────────────────────────────────────

  await page.getByLabel(/Nombre/i).fill(productName);
  await page.getByLabel(/Precio de venta/i).fill(productPrice);

  // ── 6. Submit the form ────────────────────────────────────────────────────

  await page.getByRole("button", { name: /guardar|crear producto|agregar producto/i }).click();

  // ── 7. Verify redirect to /catalog and product visible in list ────────────

  await expect(page).toHaveURL(/\/catalog$/, { timeout: 10_000 });
  await expect(page.getByText(productName)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(productPrice)).toBeVisible();
});
