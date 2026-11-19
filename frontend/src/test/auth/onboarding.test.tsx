import { QueryClient } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
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

function mockAuthenticatedOnboardingRequired() {
  server.use(
    http.get("/api/v1/auth/me", () => {
      return HttpResponse.json({
        user: DEFAULT_TEST_USER,
        requires_onboarding: true,
        business: null,
      });
    }),
  );
}

describe("Onboarding modal (Design-Blind)", () => {
  it("renderiza diálogo accesible con campos semánticos y catálogo de países", async () => {
    mockAuthenticatedOnboardingRequired();
    renderApp(["/"]);

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");

    const modal = within(dialog);
    expect(
      modal.getByRole("heading", { level: 2, name: "¡Bienvenido! Configura tu comercio" }),
    ).toBeInTheDocument();
    expect(
      modal.getByText(
        "Para comenzar a registrar ventas, indica el nombre de tu negocio y tu país de operación.",
      ),
    ).toBeInTheDocument();

    const nameInput = modal.getByLabelText(/Nombre del negocio/i);
    expect(nameInput).toBeRequired();
    expect(nameInput).toHaveAttribute("placeholder", "Ej. Kiosco Central");
    expect(nameInput).toHaveAttribute("maxLength", "100");

    const countrySelect = modal.getByRole("combobox", { name: /País de operación/i });
    expect(countrySelect).toBeRequired();
    expect(
      modal.getByText("Determina la moneda y la zona horaria de tus cierres de caja."),
    ).toBeInTheDocument();
    expect(within(countrySelect).getAllByRole("option").length).toBeGreaterThan(1);

    expect(modal.getByRole("button", { name: "Crear Comercio y Entrar" })).toBeInTheDocument();
  });

  it("rechaza nombre en blanco, >100 caracteres o país faltante sin llamar a la API", async () => {
    const user = userEvent.setup();
    let onboardingCalls = 0;

    mockAuthenticatedOnboardingRequired();
    server.use(
      http.post("/api/v1/auth/onboarding", () => {
        onboardingCalls += 1;
        return HttpResponse.json(
          { ...DEFAULT_TEST_BUSINESS, created_at: "2026-01-01T00:00:00Z" },
          { status: 201 },
        );
      }),
    );

    renderApp(["/"]);
    const dialog = await screen.findByRole("dialog");
    const modal = within(dialog);
    const nameInput = modal.getByLabelText(/Nombre del negocio/i);
    const countrySelect = modal.getByRole("combobox", { name: /País de operación/i });
    const submitButton = modal.getByRole("button", { name: "Crear Comercio y Entrar" });

    // Caso 1: nombre solo espacios y país vacío
    await user.type(nameInput, "   ");
    await user.click(submitButton);
    expect(await modal.findByRole("alert")).toBeInTheDocument();
    expect(nameInput).toHaveAttribute("aria-invalid", "true");
    expect(onboardingCalls).toBe(0);

    // Caso 2: nombre > 100 caracteres
    await user.selectOptions(countrySelect, "AR");
    fireEvent.change(nameInput, { target: { value: "A".repeat(101) } });
    await user.click(submitButton);
    expect(await modal.findByRole("alert")).toBeInTheDocument();
    expect(nameInput).toHaveAttribute("aria-invalid", "true");
    expect(onboardingCalls).toBe(0);

    // Caso 3: nombre válido sin país seleccionado
    await user.clear(nameInput);
    await user.type(nameInput, "Kiosco Central");
    await user.selectOptions(countrySelect, "");
    await user.click(submitButton);
    expect(await modal.findByRole("alert")).toBeInTheDocument();
    expect(countrySelect).toHaveAttribute("aria-invalid", "true");
    expect(onboardingCalls).toBe(0);
  });

  it("no se cierra con Escape ni permite acceder al mostrador sin comercio", async () => {
    const user = userEvent.setup();
    mockAuthenticatedOnboardingRequired();

    renderApp(["/"]);
    const dialog = await screen.findByRole("dialog");

    await user.keyboard("{Escape}");
    expect(dialog).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    expect(screen.queryByText(DEFAULT_TEST_BUSINESS.name)).not.toBeInTheDocument();
  });

  it("envía 201, actualiza metadatos públicos y redirige a /", async () => {
    const user = userEvent.setup();
    let capturedBody: unknown = null;

    mockAuthenticatedOnboardingRequired();
    server.use(
      http.post("/api/v1/auth/onboarding", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json(
          {
            id: "33333333-3333-4333-8333-333333333333",
            name: "Almacén Norte",
            country: "AR",
            timezone: "America/Argentina/Buenos_Aires",
            role: "owner",
            created_at: "2026-01-01T00:00:00Z",
          },
          { status: 201 },
        );
      }),
    );

    const { router } = renderApp(["/"]);
    const dialog = await screen.findByRole("dialog");
    const modal = within(dialog);

    await user.type(modal.getByLabelText(/Nombre del negocio/i), "Almacén Norte");
    await user.selectOptions(modal.getByRole("combobox", { name: /País de operación/i }), "AR");
    await user.click(modal.getByRole("button", { name: "Crear Comercio y Entrar" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect(capturedBody).toMatchObject({ name: "Almacén Norte", country: "AR" });
    expect(router.state.location.pathname).toBe("/");
    expect(screen.getByText("Almacén Norte")).toBeInTheDocument();

    const stored = JSON.parse(localStorage.getItem("rvm.auth.context") ?? "{}") as {
      requires_onboarding?: boolean;
      business?: { name?: string; country?: string };
    };
    expect(stored.requires_onboarding).toBe(false);
    expect(stored.business?.name).toBe("Almacén Norte");
    expect(stored.business?.country).toBe("AR");
  });

  it("reconcilia vía /me cuando POST /onboarding devuelve 409 con negocio ya existente", async () => {
    const user = userEvent.setup();
    let meCalls = 0;

    server.use(
      http.get("/api/v1/auth/me", () => {
        meCalls += 1;
        if (meCalls === 1) {
          return HttpResponse.json({
            user: DEFAULT_TEST_USER,
            requires_onboarding: true,
            business: null,
          });
        }
        return HttpResponse.json({
          user: DEFAULT_TEST_USER,
          requires_onboarding: false,
          business: DEFAULT_TEST_BUSINESS,
        });
      }),
      http.post("/api/v1/auth/onboarding", () => {
        return HttpResponse.json(
          {
            code: "BUSINESS_ALREADY_EXISTS",
            message: "El usuario ya posee un comercio",
            details: null,
          },
          { status: 409 },
        );
      }),
    );

    const { router } = renderApp(["/"]);
    const dialog = await screen.findByRole("dialog");
    const modal = within(dialog);

    await user.type(modal.getByLabelText(/Nombre del negocio/i), "Kiosco Central");
    await user.selectOptions(modal.getByRole("combobox", { name: /País de operación/i }), "AR");
    await user.click(modal.getByRole("button", { name: "Crear Comercio y Entrar" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect(meCalls).toBeGreaterThanOrEqual(2);
    expect(router.state.location.pathname).toBe("/");
    expect(screen.getByText(DEFAULT_TEST_BUSINESS.name)).toBeInTheDocument();
  });

  it("muestra alerta en modal si 409 no encuentra negocio activo en /me", async () => {
    const user = userEvent.setup();
    mockAuthenticatedOnboardingRequired();
    server.use(
      http.post("/api/v1/auth/onboarding", () => {
        return HttpResponse.json(
          {
            code: "BUSINESS_ALREADY_EXISTS",
            message: "Conflicto al crear comercio",
            details: null,
          },
          { status: 409 },
        );
      }),
    );

    renderApp(["/"]);
    const dialog = await screen.findByRole("dialog");
    const modal = within(dialog);

    await user.type(modal.getByLabelText(/Nombre del negocio/i), "Kiosco Central");
    await user.selectOptions(modal.getByRole("combobox", { name: /País de operación/i }), "AR");
    await user.click(modal.getByRole("button", { name: "Crear Comercio y Entrar" }));

    expect(await modal.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("intenta /refresh una vez ante 401 en /onboarding y redirige a /login si refresh falla", async () => {
    const user = userEvent.setup();
    let refreshCalls = 0;

    mockAuthenticatedOnboardingRequired();
    server.use(
      http.post("/api/v1/auth/onboarding", () => {
        return HttpResponse.json(
          { code: "UNAUTHENTICATED", message: "Token expirado", details: null },
          { status: 401 },
        );
      }),
      http.post("/api/v1/auth/refresh", () => {
        refreshCalls += 1;
        return HttpResponse.json(
          { code: "UNAUTHENTICATED", message: "Refresh inválido", details: null },
          { status: 401 },
        );
      }),
    );

    const { router } = renderApp(["/"]);
    const dialog = await screen.findByRole("dialog");
    const modal = within(dialog);

    await user.type(modal.getByLabelText(/Nombre del negocio/i), "Kiosco Central");
    await user.selectOptions(modal.getByRole("combobox", { name: /País de operación/i }), "AR");
    await user.click(modal.getByRole("button", { name: "Crear Comercio y Entrar" }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/login");
    });
    expect(refreshCalls).toBe(1);
    expect(localStorage.getItem("rvm.auth.context")).toBeNull();
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
