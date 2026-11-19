import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Providers } from "@/app/providers";
import { routes } from "@/app/router";
import { DEFAULT_TEST_BUSINESS, DEFAULT_TEST_USER } from "../mocks/handlers";
import { server } from "../mocks/server";

function renderApp(initialEntries: string[] = ["/"]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
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

describe("Session management, HttpOnly cookies, route guards, and logout", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('envía credentials: "include" en las peticiones de autenticación', async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderApp(["/login"]);
    await user.type(await screen.findByLabelText(/Correo electrónico/i), "dueno@negocio.com");
    await user.type(screen.getByLabelText(/Contraseña/i), "ClaveSegura123");
    await user.click(screen.getByRole("button", { name: "Iniciar Sesión" }));

    await screen.findByRole("button", { name: "Cerrar sesión" });

    const authCalls = fetchSpy.mock.calls.filter(([input]) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      return url.includes("/api/v1/auth/");
    });

    expect(authCalls.length).toBeGreaterThanOrEqual(2);
    for (const [input, init] of authCalls) {
      const credentials =
        init?.credentials ?? (input instanceof Request ? input.credentials : undefined);
      expect(credentials).toBe("include");
    }
  });

  it("persiste solo metadatos públicos y nunca almacena JWT, tokens ni contraseñas", async () => {
    const user = userEvent.setup();
    const secretPassword = "MiClaveSuperSecreta!99";

    renderApp(["/login"]);
    await user.type(await screen.findByLabelText(/Correo electrónico/i), "dueno@negocio.com");
    await user.type(screen.getByLabelText(/Contraseña/i), secretPassword);
    await user.click(screen.getByRole("button", { name: "Iniciar Sesión" }));

    await screen.findByRole("button", { name: "Cerrar sesión" });

    expect(sessionStorage.length).toBe(0);

    const rawContext = localStorage.getItem("rvm.auth.context");
    expect(rawContext).not.toBeNull();
    const parsed = JSON.parse(rawContext ?? "{}") as {
      user?: { id?: string; email?: string };
      requires_onboarding?: boolean;
      business?: { id?: string; name?: string; country?: string; timezone?: string; role?: string };
    };

    expect(parsed.user).toEqual(DEFAULT_TEST_USER);
    expect(parsed.requires_onboarding).toBe(false);
    expect(parsed.business).toEqual(DEFAULT_TEST_BUSINESS);

    const allLocalStorage = JSON.stringify(localStorage);
    expect(allLocalStorage).not.toContain("access_token");
    expect(allLocalStorage).not.toContain("refresh_token");
    expect(allLocalStorage).not.toContain(secretPassword);
    expect(allLocalStorage).not.toMatch(/eyJ[A-Za-z0-9_-]+\./);
  });

  it('preserva h1 "registro-venta-micro" durante bootstrapping y rehidrata sesión vía GET /me', async () => {
    let resolveMe!: () => void;
    const pendingMe = new Promise<void>((resolve) => {
      resolveMe = resolve;
    });

    server.use(
      http.get("/api/v1/auth/me", async () => {
        await pendingMe;
        return HttpResponse.json({
          user: DEFAULT_TEST_USER,
          requires_onboarding: false,
          business: DEFAULT_TEST_BUSINESS,
        });
      }),
    );

    renderApp(["/"]);

    // Desde el primer render (bootstrapping) el h1 debe existir para compatibilidad
    expect(
      screen.getByRole("heading", { level: 1, name: "registro-venta-micro" }),
    ).toBeInTheDocument();

    resolveMe();

    expect(await screen.findByRole("button", { name: "Cerrar sesión" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 1, name: "registro-venta-micro" }),
    ).toBeInTheDocument();
    expect(screen.getByText(DEFAULT_TEST_BUSINESS.name)).toBeInTheDocument();
    expect(screen.getByText(DEFAULT_TEST_USER.email)).toBeInTheDocument();
  });

  it("ejecuta refresh silencioso cuando GET /me responde 401 y restaura sesión con 200", async () => {
    let refreshCalls = 0;

    server.use(
      http.get("/api/v1/auth/me", () => {
        return HttpResponse.json(
          { code: "UNAUTHENTICATED", message: "Access token expirado", details: null },
          { status: 401 },
        );
      }),
      http.post("/api/v1/auth/refresh", () => {
        refreshCalls += 1;
        return HttpResponse.json({
          user: DEFAULT_TEST_USER,
          requires_onboarding: false,
          business: DEFAULT_TEST_BUSINESS,
        });
      }),
    );

    const { router } = renderApp(["/"]);

    expect(await screen.findByRole("button", { name: "Cerrar sesión" })).toBeInTheDocument();
    expect(refreshCalls).toBe(1);
    expect(router.state.location.pathname).toBe("/");
    expect(screen.getByText(DEFAULT_TEST_BUSINESS.name)).toBeInTheDocument();
  });

  it("limpia metadatos y redirige a /login cuando /me y /refresh responden 401", async () => {
    localStorage.setItem(
      "rvm.auth.context",
      JSON.stringify({
        user: DEFAULT_TEST_USER,
        requires_onboarding: false,
        business: DEFAULT_TEST_BUSINESS,
      }),
    );

    const { router } = renderApp(["/"]);

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/login");
    });
    expect(localStorage.getItem("rvm.auth.context")).toBeNull();
    expect(await screen.findByRole("button", { name: "Iniciar Sesión" })).toBeInTheDocument();
  });

  it("redirige automáticamente desde /login hacia / cuando ya existe negocio activo", async () => {
    server.use(
      http.get("/api/v1/auth/me", () => {
        return HttpResponse.json({
          user: DEFAULT_TEST_USER,
          requires_onboarding: false,
          business: DEFAULT_TEST_BUSINESS,
        });
      }),
    );

    const { router } = renderApp(["/login"]);

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/");
    });
    expect(await screen.findByRole("button", { name: "Cerrar sesión" })).toBeInTheDocument();
  });

  it('cierra sesión al activar "Cerrar sesión", limpia localStorage y redirige a /login', async () => {
    const user = userEvent.setup();
    let logoutCalls = 0;

    server.use(
      http.get("/api/v1/auth/me", () => {
        return HttpResponse.json({
          user: DEFAULT_TEST_USER,
          requires_onboarding: false,
          business: DEFAULT_TEST_BUSINESS,
        });
      }),
      http.post("/api/v1/auth/logout", () => {
        logoutCalls += 1;
        return new HttpResponse(null, { status: 204 });
      }),
    );

    const { router } = renderApp(["/"]);
    const logoutButton = await screen.findByRole("button", { name: "Cerrar sesión" });

    await user.click(logoutButton);

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/login");
    });
    expect(logoutCalls).toBe(1);
    expect(localStorage.getItem("rvm.auth.context")).toBeNull();
  });

  it("preserva contexto público cacheado y no redirige a /login ante error de red en GET /me", async () => {
    const cachedContext = {
      user: DEFAULT_TEST_USER,
      requires_onboarding: false,
      business: DEFAULT_TEST_BUSINESS,
    };
    localStorage.setItem("rvm.auth.context", JSON.stringify(cachedContext));

    server.use(
      http.get("/api/v1/auth/me", () => {
        return HttpResponse.error();
      }),
    );

    const { router } = renderApp(["/"]);

    expect(await screen.findByRole("button", { name: "Cerrar sesión" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
    expect(screen.getByText(DEFAULT_TEST_BUSINESS.name)).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem("rvm.auth.context") ?? "{}")).toEqual(cachedContext);
  });

  it("preserva contexto público ante 503 transitorio en GET /api/v1/auth/me", async () => {
    const cachedContext = {
      user: DEFAULT_TEST_USER,
      requires_onboarding: false,
      business: DEFAULT_TEST_BUSINESS,
    };
    localStorage.setItem("rvm.auth.context", JSON.stringify(cachedContext));

    server.use(
      http.get("/api/v1/auth/me", () => {
        return HttpResponse.json(
          { code: "SERVICE_UNAVAILABLE", message: "Temporalmente caído", details: null },
          { status: 503 },
        );
      }),
    );

    const { router } = renderApp(["/"]);

    expect(await screen.findByRole("button", { name: "Cerrar sesión" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
    expect(screen.getByText(DEFAULT_TEST_BUSINESS.name)).toBeInTheDocument();
  });

  it("limpia contexto local y redirige a /login aunque POST /api/v1/auth/logout falle por red", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/v1/auth/me", () => {
        return HttpResponse.json({
          user: DEFAULT_TEST_USER,
          requires_onboarding: false,
          business: DEFAULT_TEST_BUSINESS,
        });
      }),
      http.post("/api/v1/auth/logout", () => {
        return HttpResponse.error();
      }),
    );

    const { router } = renderApp(["/"]);
    const logoutButton = await screen.findByRole("button", { name: "Cerrar sesión" });
    await user.click(logoutButton);

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/login");
    });
    expect(localStorage.getItem("rvm.auth.context")).toBeNull();
  });
});
