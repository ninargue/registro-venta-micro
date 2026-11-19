import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
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

describe("Login screen (Design-Blind)", () => {
  it("renderiza los elementos semánticos requeridos en /login en estado inicial", async () => {
    renderApp(["/login"]);

    const region = await screen.findByRole("region", {
      name: "Tarjeta de inicio de sesión",
    });
    expect(region).toBeInTheDocument();

    expect(
      screen.getByRole("heading", { level: 1, name: "registro-venta-micro" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Ingresa las credenciales de tu negocio para comenzar a operar."),
    ).toBeInTheDocument();

    const emailInput = screen.getByLabelText(/Correo electrónico/i);
    expect(emailInput).toBeRequired();
    expect(emailInput).toHaveAttribute("placeholder", "dueño@negocio.com");

    const passwordInput = screen.getByLabelText(/Contraseña/i);
    expect(passwordInput).toBeRequired();
    expect(passwordInput).toHaveAttribute("type", "password");

    expect(screen.getByRole("button", { name: "Iniciar Sesión" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Alternar modo claro / modo oscuro" }),
    ).toBeInTheDocument();
  });

  it("rechaza email vacío, email inválido o contraseña vacía antes de llamar a la API", async () => {
    const user = userEvent.setup();
    let loginCalls = 0;

    server.use(
      http.post("/api/v1/auth/login", () => {
        loginCalls += 1;
        return HttpResponse.json({
          user: DEFAULT_TEST_USER,
          requires_onboarding: false,
          business: DEFAULT_TEST_BUSINESS,
        });
      }),
    );

    renderApp(["/login"]);
    const submitButton = await screen.findByRole("button", { name: "Iniciar Sesión" });

    // Caso 1: ambos vacíos
    await user.click(submitButton);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByLabelText(/Correo electrónico/i)).toHaveAttribute("aria-invalid", "true");
    expect(loginCalls).toBe(0);

    // Caso 2: formato de email inválido
    await user.type(screen.getByLabelText(/Correo electrónico/i), "correo-invalido");
    await user.type(screen.getByLabelText(/Contraseña/i), "secreto123");
    await user.click(submitButton);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByLabelText(/Correo electrónico/i)).toHaveAttribute("aria-invalid", "true");
    expect(loginCalls).toBe(0);

    // Caso 3: email válido y contraseña vacía
    await user.clear(screen.getByLabelText(/Correo electrónico/i));
    await user.type(screen.getByLabelText(/Correo electrónico/i), "dueno@negocio.com");
    await user.clear(screen.getByLabelText(/Contraseña/i));
    await user.click(submitButton);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByLabelText(/Contraseña/i)).toHaveAttribute("aria-invalid", "true");
    expect(loginCalls).toBe(0);
  });

  it("deshabilita el envío en estado loading para evitar peticiones duplicadas", async () => {
    const user = userEvent.setup();
    let loginCalls = 0;
    let resolveLogin!: () => void;
    const pendingLogin = new Promise<void>((resolve) => {
      resolveLogin = resolve;
    });

    server.use(
      http.post("/api/v1/auth/login", async () => {
        loginCalls += 1;
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

    await user.click(submitButton);
    expect(loginCalls).toBe(1);

    resolveLogin();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Cerrar sesión" })).toBeInTheDocument();
    });
  });

  it("alterna el tema claro/oscuro y actualiza aria-pressed", async () => {
    const user = userEvent.setup();
    renderApp(["/login"]);

    const toggle = await screen.findByRole("button", {
      name: "Alternar modo claro / modo oscuro",
    });
    const initialPressed = toggle.getAttribute("aria-pressed");
    expect(["true", "false"]).toContain(initialPressed);

    await user.click(toggle);
    const nextPressed = toggle.getAttribute("aria-pressed");
    expect(nextPressed).not.toBe(initialPressed);
    expect(document.documentElement).toHaveAttribute(
      "data-theme",
      nextPressed === "true" ? "dark" : "light",
    );

    await user.click(toggle);
    expect(toggle.getAttribute("aria-pressed")).toBe(initialPressed);
  });

  it("redirige a / cuando login 200 retorna requires_onboarding: false", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/auth/login", () => {
        return HttpResponse.json({
          user: DEFAULT_TEST_USER,
          requires_onboarding: false,
          business: DEFAULT_TEST_BUSINESS,
        });
      }),
    );

    const { router } = renderApp(["/login"]);
    await user.type(await screen.findByLabelText(/Correo electrónico/i), "dueno@negocio.com");
    await user.type(screen.getByLabelText(/Contraseña/i), "ClaveSegura123");
    await user.click(screen.getByRole("button", { name: "Iniciar Sesión" }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/");
    });
    expect(await screen.findByText(DEFAULT_TEST_BUSINESS.name)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cerrar sesión" })).toBeInTheDocument();
  });

  it("abre el modal de onboarding cuando login 200 retorna requires_onboarding: true", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/auth/login", () => {
        return HttpResponse.json({
          user: DEFAULT_TEST_USER,
          requires_onboarding: true,
          business: null,
        });
      }),
    );

    renderApp(["/login"]);
    await user.type(await screen.findByLabelText(/Correo electrónico/i), "dueno@negocio.com");
    await user.type(screen.getByLabelText(/Contraseña/i), "ClaveSegura123");
    await user.click(screen.getByRole("button", { name: "Iniciar Sesión" }));

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(
      screen.getByRole("heading", { level: 2, name: "¡Bienvenido! Configura tu comercio" }),
    ).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Cerrar sesión" })).toBeInTheDocument();
  });

  it("muestra alerta accesible ante 401 INVALID_CREDENTIALS sin guardar sesión", async () => {
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

    const { router } = renderApp(["/login"]);
    await user.type(await screen.findByLabelText(/Correo electrónico/i), "dueno@negocio.com");
    await user.type(screen.getByLabelText(/Contraseña/i), "incorrecta");
    await user.click(screen.getByRole("button", { name: "Iniciar Sesión" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Correo electrónico o contraseña incorrectos.");
    expect(router.state.location.pathname).toBe("/login");
    expect(localStorage.getItem("rvm.auth.context")).toBeNull();
  });

  it.each([
    {
      status: 422,
      code: "VALIDATION_ERROR",
      message: "Datos inválidos",
      expectedAlert: "Datos inválidos",
    },
    {
      status: 429,
      code: "RATE_LIMIT_EXCEEDED",
      message: "Demasiados intentos",
      expectedAlert: "Demasiados intentos fallidos. Espera un momento antes de volver a intentar.",
    },
    {
      status: 502,
      code: "AUTH_UPSTREAM_UNAVAILABLE",
      message: "Servicio no disponible",
      expectedAlert: "El servicio de autenticación no está disponible temporalmente.",
    },
    {
      status: 503,
      code: "AUTH_UPSTREAM_TIMEOUT",
      message: "Tiempo de espera agotado",
      expectedAlert: "El servicio tardó demasiado en responder. Intenta nuevamente.",
    },
  ])(
    "muestra alerta accesible, sale de loading y conserva email ante HTTP $status",
    async ({ status, code, message, expectedAlert }) => {
      const user = userEvent.setup();
      server.use(
        http.post("/api/v1/auth/login", () => {
          return HttpResponse.json({ code, message, details: null }, { status });
        }),
      );

      renderApp(["/login"]);
      const emailInput = await screen.findByLabelText(/Correo electrónico/i);
      await user.type(emailInput, "dueno@negocio.com");
      await user.type(screen.getByLabelText(/Contraseña/i), "ClaveSegura123");
      await user.click(screen.getByRole("button", { name: "Iniciar Sesión" }));

      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(expectedAlert);
      expect(emailInput).toHaveValue("dueno@negocio.com");
      expect(screen.getByRole("button", { name: "Iniciar Sesión" })).toBeEnabled();
    },
  );

  it("muestra alerta accesible y conserva email ante error de red", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/auth/login", () => {
        return HttpResponse.error();
      }),
    );

    renderApp(["/login"]);
    const emailInput = await screen.findByLabelText(/Correo electrónico/i);
    await user.type(emailInput, "dueno@negocio.com");
    await user.type(screen.getByLabelText(/Contraseña/i), "ClaveSegura123");
    await user.click(screen.getByRole("button", { name: "Iniciar Sesión" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "No se pudo conectar con el servidor. Verifica tu conexión e intenta nuevamente.",
    );
    expect(emailInput).toHaveValue("dueno@negocio.com");
    expect(screen.getByRole("button", { name: "Iniciar Sesión" })).toBeEnabled();
  });
});
