import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { Providers } from "@/app/providers";
import { routes } from "@/app/router";
import { DEFAULT_TEST_BUSINESS, DEFAULT_TEST_USER } from "../mocks/handlers";
import { server } from "../mocks/server";

function renderApp(initialEntries: string[] = ["/login"]) {
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

describe("UI Spec State Catalog & Accessibility (auth-onboarding-ui-spec.json)", () => {
  describe("login-screen states", () => {
    it("estado empty: expone todos los roles/labels ARIA requeridos sin alertas", async () => {
      renderApp(["/login"]);

      const region = await screen.findByRole("region", {
        name: "Tarjeta de inicio de sesión",
      });
      expect(region).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { level: 1, name: "registro-venta-micro" }),
      ).toBeInTheDocument();
      expect(screen.getByLabelText(/Correo electrónico/i)).toHaveValue("");
      expect(screen.getByLabelText(/Contraseña/i)).toHaveValue("");
      expect(screen.getByRole("button", { name: "Iniciar Sesión" })).toBeEnabled();
      expect(
        screen.getByRole("button", { name: "Alternar modo claro / modo oscuro" }),
      ).toHaveAttribute("aria-pressed");
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("estado ready: permite completar credenciales y navegar por teclado con Tab", async () => {
      const user = userEvent.setup();
      renderApp(["/login"]);

      const emailInput = await screen.findByLabelText(/Correo electrónico/i);
      const passwordInput = screen.getByLabelText(/Contraseña/i);
      const submitButton = screen.getByRole("button", { name: "Iniciar Sesión" });

      await user.click(emailInput);
      await user.keyboard("dueno@negocio.com");
      await user.tab();
      expect(passwordInput).toHaveFocus();
      await user.keyboard("ClaveSegura123");

      expect(emailInput).toHaveValue("dueno@negocio.com");
      expect(passwordInput).toHaveValue("ClaveSegura123");
      expect(submitButton).toBeEnabled();
    });

    it("estado loading: deshabilita botón de envío mientras la petición está en curso", async () => {
      const user = userEvent.setup();
      let resolveLogin!: () => void;
      const pendingLogin = new Promise<void>((resolve) => {
        resolveLogin = resolve;
      });

      server.use(
        http.post("/api/v1/auth/login", async () => {
          await pendingLogin;
          return HttpResponse.json({
            user: DEFAULT_TEST_USER,
            requires_onboarding: false,
            business: DEFAULT_TEST_BUSINESS,
          });
        }),
      );

      renderApp(["/login"]);
      await user.type(await screen.findByLabelText(/Correo electrónico/i), "dueno@negocio.com");
      await user.type(screen.getByLabelText(/Contraseña/i), "ClaveSegura123");

      const submitButton = screen.getByRole("button", { name: "Iniciar Sesión" });
      await user.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
      });

      resolveLogin();
      await screen.findByRole("button", { name: "Cerrar sesión" });
    });

    it("estado error: anuncia mensaje en role=alert accesible", async () => {
      const user = userEvent.setup();
      server.use(
        http.post("/api/v1/auth/login", () => {
          return HttpResponse.json(
            {
              code: "INVALID_CREDENTIALS",
              message: "Credenciales inválidas",
              details: null,
            },
            { status: 401 },
          );
        }),
      );

      renderApp(["/login"]);
      await user.type(await screen.findByLabelText(/Correo electrónico/i), "dueno@negocio.com");
      await user.type(screen.getByLabelText(/Contraseña/i), "incorrecta");
      await user.click(screen.getByRole("button", { name: "Iniciar Sesión" }));

      const alert = await screen.findByRole("alert");
      expect(alert).toBeVisible();
      expect(alert.textContent.trim().length).toBeGreaterThan(0);
    });
  });

  describe("onboarding-modal states", () => {
    function mockOnboardingSession() {
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

    it("estado ready: expone dialog modal accesible y navegación por teclado", async () => {
      const user = userEvent.setup();
      mockOnboardingSession();
      renderApp(["/"]);

      const dialog = await screen.findByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");

      const modal = within(dialog);
      const nameInput = modal.getByLabelText(/Nombre del negocio/i);
      const countrySelect = modal.getByRole("combobox", { name: /País de operación/i });
      const submitButton = modal.getByRole("button", { name: "Crear Comercio y Entrar" });

      expect(
        modal.getByRole("heading", { level: 2, name: "¡Bienvenido! Configura tu comercio" }),
      ).toBeInTheDocument();
      expect(submitButton).toBeEnabled();

      await user.click(nameInput);
      await user.keyboard("Kiosco Central");
      await user.tab();
      expect(countrySelect).toHaveFocus();
      await user.selectOptions(countrySelect, "AR");
      await user.tab();
      expect(submitButton).toHaveFocus();
    });

    it("estado loading: deshabilita botón mientras se crea el comercio", async () => {
      const user = userEvent.setup();
      let resolveOnboarding!: () => void;
      const pendingOnboarding = new Promise<void>((resolve) => {
        resolveOnboarding = resolve;
      });

      mockOnboardingSession();
      server.use(
        http.post("/api/v1/auth/onboarding", async () => {
          await pendingOnboarding;
          return HttpResponse.json(
            { ...DEFAULT_TEST_BUSINESS, created_at: "2026-01-01T00:00:00Z" },
            { status: 201 },
          );
        }),
      );

      renderApp(["/"]);
      const dialog = await screen.findByRole("dialog");
      const modal = within(dialog);

      await user.type(modal.getByLabelText(/Nombre del negocio/i), "Kiosco Central");
      await user.selectOptions(modal.getByRole("combobox", { name: /País de operación/i }), "AR");

      const submitButton = modal.getByRole("button", { name: "Crear Comercio y Entrar" });
      await user.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
      });

      resolveOnboarding();
      await waitFor(() => {
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      });
    });

    it("estado error: muestra alerta accesible dentro del diálogo ante fallo de validación", async () => {
      const user = userEvent.setup();
      mockOnboardingSession();
      renderApp(["/"]);

      const dialog = await screen.findByRole("dialog");
      const modal = within(dialog);

      await user.click(modal.getByRole("button", { name: "Crear Comercio y Entrar" }));

      const alert = await modal.findByRole("alert");
      expect(alert).toBeVisible();
      expect(modal.getByLabelText(/Nombre del negocio/i)).toHaveAttribute("aria-invalid", "true");
    });
  });
});
