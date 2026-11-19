import { expect, test } from "@playwright/test";

test("camino crítico: / -> /login -> onboarding -> / -> recarga -> cerrar sesión -> /login", async ({
  page,
}) => {
  let authenticated = false;
  let business: {
    id: string;
    name: string;
    country: string;
    timezone: string;
    role: "owner";
  } | null = null;

  const user = {
    id: "11111111-1111-4111-8111-111111111111",
    email: "dueno@negocio.com",
  };

  await page.route("**/api/v1/auth/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (url.pathname === "/api/v1/auth/me" && request.method() === "GET") {
      if (!authenticated) {
        await route.fulfill({
          status: 401,
          contentType: "application/json",
          body: JSON.stringify({
            code: "UNAUTHENTICATED",
            message: "No autenticado",
            details: null,
          }),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user,
          requires_onboarding: business === null,
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

    if (url.pathname === "/api/v1/auth/login" && request.method() === "POST") {
      authenticated = true;
      business = null;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user,
          requires_onboarding: true,
          business: null,
        }),
      });
      return;
    }

    if (url.pathname === "/api/v1/auth/onboarding" && request.method() === "POST") {
      const payload = request.postDataJSON() as { name: string; country: string };
      business = {
        id: "22222222-2222-4222-8222-222222222222",
        name: payload.name,
        country: payload.country,
        timezone: "America/Argentina/Buenos_Aires",
        role: "owner",
      };
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          ...business,
          created_at: "2026-01-01T00:00:00Z",
        }),
      });
      return;
    }

    if (url.pathname === "/api/v1/auth/logout" && request.method() === "POST") {
      authenticated = false;
      business = null;
      await route.fulfill({ status: 204 });
      return;
    }

    await route.fallback();
  });

  // 1. Entrada anónima a / redirige a /login
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("registro-venta-micro");

  // 2. Login con usuario que requiere onboarding
  await page.getByLabel(/Correo electrónico/i).fill("dueno@negocio.com");
  await page.getByLabel(/Contraseña/i).fill("ClaveSegura123");
  await page.getByRole("button", { name: "Iniciar Sesión" }).click();

  // 3. Modal de onboarding obligatorio
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog).toHaveAttribute("aria-modal", "true");

  await dialog.getByLabel(/Nombre del negocio/i).fill("Kiosco Central");
  await dialog.getByRole("combobox", { name: /País de operación/i }).selectOption("AR");
  await dialog.getByRole("button", { name: "Crear Comercio y Entrar" }).click();

  // 4. Redirección a / con negocio creado
  await expect(dialog).toBeHidden();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText("Kiosco Central")).toBeVisible();

  // 5. Recarga conserva sesión vía /me
  await page.reload();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText("Kiosco Central")).toBeVisible();

  // 6. Cerrar sesión limpia contexto y vuelve a /login
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page).toHaveURL(/\/login$/);
  const authContext = await page.evaluate(() => localStorage.getItem("rvm.auth.context"));
  expect(authContext).toBeNull();
});
