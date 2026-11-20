import { QueryClient } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { Providers } from "@/app/providers";
import { routes } from "@/app/router";
import { DEFAULT_TEST_BUSINESS, DEFAULT_TEST_USER } from "../mocks/handlers";
import { server } from "../mocks/server";

function renderApp(initialEntries: string[]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const router = createMemoryRouter(routes, { initialEntries });

  return {
    router,
    ...render(
      <Providers queryClient={queryClient}>
        <RouterProvider router={router} />
      </Providers>,
    ),
  };
}

function mockAuthenticated() {
  server.use(
    http.get("/api/v1/auth/me", () =>
      HttpResponse.json({
        user: DEFAULT_TEST_USER,
        requires_onboarding: false,
        business: DEFAULT_TEST_BUSINESS,
      }),
    ),
  );
}

describe("Navegación persistente entre módulos", () => {
  it("muestra el menú con Inicio, Catálogo y Reporte diario a un usuario autenticado", async () => {
    mockAuthenticated();
    renderApp(["/"]);

    const nav = await screen.findByRole("navigation", { name: "Navegación principal" });

    expect(within(nav).getByRole("link", { name: "Inicio" })).toHaveAttribute("href", "/");
    expect(within(nav).getByRole("link", { name: "Catálogo" })).toHaveAttribute("href", "/catalog");
    expect(within(nav).getByRole("link", { name: "Reporte diario" })).toHaveAttribute(
      "href",
      "/reports/daily",
    );
  });

  it('marca solo la entrada de la ruta actual con aria-current="page"', async () => {
    mockAuthenticated();
    renderApp(["/"]);

    const nav = await screen.findByRole("navigation", { name: "Navegación principal" });

    expect(within(nav).getByRole("link", { name: "Inicio" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(nav).getByRole("link", { name: "Catálogo" })).not.toHaveAttribute("aria-current");
    expect(within(nav).getByRole("link", { name: "Reporte diario" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("navega al catálogo sin recargar y mantiene el menú visible", async () => {
    const user = userEvent.setup();
    mockAuthenticated();
    const { router } = renderApp(["/"]);

    const nav = await screen.findByRole("navigation", { name: "Navegación principal" });
    await user.click(within(nav).getByRole("link", { name: "Catálogo" }));

    expect(
      await screen.findByRole("heading", { level: 1, name: "Catálogo de productos" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/catalog");

    const navAfter = screen.getByRole("navigation", { name: "Navegación principal" });
    expect(within(navAfter).getByRole("link", { name: "Catálogo" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(navAfter).getByRole("link", { name: "Inicio" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("mantiene la entrada Catálogo activa en las subrutas del catálogo", async () => {
    mockAuthenticated();
    renderApp(["/catalog/new"]);

    const nav = await screen.findByRole("navigation", { name: "Navegación principal" });

    expect(within(nav).getByRole("link", { name: "Catálogo" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("muestra el menú en el reporte diario", async () => {
    mockAuthenticated();
    renderApp(["/reports/daily"]);

    const nav = await screen.findByRole("navigation", { name: "Navegación principal" });

    expect(within(nav).getByRole("link", { name: "Reporte diario" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Reporte Diario de Ventas y Margen",
      }),
    ).toBeInTheDocument();
  });

  it("no muestra el menú en /login", async () => {
    renderApp(["/login"]);

    await screen.findByRole("button", { name: "Iniciar Sesión" });

    expect(screen.queryByRole("navigation", { name: "Navegación principal" })).toBeNull();
  });

  it("no muestra el menú mientras el usuario debe completar el onboarding", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json({
          user: DEFAULT_TEST_USER,
          requires_onboarding: true,
          business: null,
        }),
      ),
    );
    renderApp(["/"]);

    await screen.findByText(DEFAULT_TEST_USER.email);

    expect(screen.queryByRole("navigation", { name: "Navegación principal" })).toBeNull();
  });

  it("muestra el mismo menú a un cajero", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json({
          user: DEFAULT_TEST_USER,
          requires_onboarding: false,
          business: { ...DEFAULT_TEST_BUSINESS, role: "cashier" },
        }),
      ),
    );
    renderApp(["/"]);

    const nav = await screen.findByRole("navigation", { name: "Navegación principal" });

    expect(within(nav).getAllByRole("link")).toHaveLength(3);
  });
});
