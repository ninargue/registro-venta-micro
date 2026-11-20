/**
 * product-create.test.tsx — Design-Blind UI tests for product creation
 *
 * Covers: R-05 (access form), R-06 (client validation), R-07 (success),
 *         R-08 (409 SKU conflict), R-09 (422 server validation)
 * Also covers: ProductForm submit behavior (B4 fix — e.preventDefault verified)
 *
 * Each test maps 1:1 to a Given/When/Then scenario in:
 *   openspec/changes/issue-44-catalogo-productos-frontend/specs/catalog-admin/spec.md
 *
 * Selector rules: ONLY semantic/accessible selectors (getByRole, getByLabelText,
 * getByText, findByRole). NO CSS class selectors. NO data-testid.
 */

import { QueryClient } from "@tanstack/react-query";
import { createEvent, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import type { RouteObject } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { Providers } from "@/app/providers";
import { CatalogListContainer } from "@/features/catalog/containers/CatalogListContainer";
import { ProductCreateContainer } from "@/features/catalog/containers/ProductCreateContainer";
import { ProductEditContainer } from "@/features/catalog/containers/ProductEditContainer";
import { ProductForm } from "@/features/catalog/components/ProductForm";
import {
  DEFAULT_PRODUCT_1,
  DEFAULT_TEST_BUSINESS,
  DEFAULT_TEST_USER,
} from "@/test/mocks/handlers";
import { server } from "@/test/mocks/server";

// ── Routes for catalog feature (mirrors router.tsx additions from T-19) ───────

const catalogRoutes: RouteObject[] = [
  {
    path: "/catalog",
    element: <CatalogListContainer />,
  },
  {
    path: "/catalog/new",
    element: <ProductCreateContainer />,
  },
  {
    path: "/catalog/:productId/edit",
    element: <ProductEditContainer />,
  },
  {
    path: "/",
    element: <div>Home</div>,
  },
];

// ── Render helper ─────────────────────────────────────────────────────────────

function renderCatalog(initialEntries: string[] = ["/catalog"]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  // Provide an authenticated session so catalog routes don't redirect to /login
  server.use(
    http.get("/api/v1/auth/me", () => {
      return HttpResponse.json({
        user: DEFAULT_TEST_USER,
        requires_onboarding: false,
        business: DEFAULT_TEST_BUSINESS,
      });
    }),
  );

  const router = createMemoryRouter(catalogRoutes, { initialEntries });

  return {
    router,
    queryClient,
    ...render(
      <Providers queryClient={queryClient}>
        <RouterProvider router={router} />
      </Providers>,
    ),
  };
}

// ── ProductForm — submit (B4: e.preventDefault verified) ─────────────────────

describe("ProductForm — submit", () => {
  it("previene el envío nativo del formulario (preventDefault)", () => {
    const onSubmit = vi.fn();
    const { container } = render(
      <ProductForm mode="create" onSubmit={onSubmit} onCancel={vi.fn()} />,
    );
    const form = container.querySelector("form") as HTMLFormElement;

    const event = createEvent.submit(form);
    fireEvent(form, event);

    expect(event.defaultPrevented).toBe(true);
    expect(onSubmit).toHaveBeenCalledOnce();
  });
});

// ── R-05: Acceso al formulario de alta ────────────────────────────────────────

describe("R-05: Acceso al formulario de alta de producto", () => {
  it("botón 'Agregar producto' navega a /catalog/new con todos los campos del formulario", async () => {
    const user = userEvent.setup();
    const { router } = renderCatalog();

    await screen.findByRole("heading", { name: /Catálogo de productos/i });

    const addButton = screen.getByRole("button", { name: /agregar producto|nuevo producto/i });
    await user.click(addButton);

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/catalog/new");
    });

    // Required fields
    expect(await screen.findByLabelText(/Nombre/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Precio de venta/i)).toBeInTheDocument();

    // Optional fields
    expect(screen.queryByLabelText(/código|SKU/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/costo/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/stock/i)).toBeInTheDocument();
  });
});

// ── R-06: Validación client-side ──────────────────────────────────────────────

describe("R-06: Validación client-side en formulario de alta", () => {
  it("nombre vacío → NO invoca POST, campo con aria-invalid='true', mensaje en role='alert'", async () => {
    const user = userEvent.setup();
    let postCalled = false;

    server.use(
      http.post("/api/v1/catalog/products", () => {
        postCalled = true;
        return HttpResponse.json({}, { status: 201 });
      }),
    );

    renderCatalog(["/catalog/new"]);

    const submitButton = await screen.findByRole("button", {
      name: /guardar|crear producto|agregar producto/i,
    });
    await user.click(submitButton);

    await waitFor(() => {
      expect(postCalled).toBe(false);
    });

    expect(screen.getByLabelText(/Nombre/i)).toHaveAttribute("aria-invalid", "true");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("precio cero → NO invoca POST, mensaje de error accesible", async () => {
    const user = userEvent.setup();
    let postCalled = false;

    server.use(
      http.post("/api/v1/catalog/products", () => {
        postCalled = true;
        return HttpResponse.json({}, { status: 201 });
      }),
    );

    renderCatalog(["/catalog/new"]);

    const nameField = await screen.findByLabelText(/Nombre/i);
    await user.type(nameField, "Producto Test");

    const priceField = screen.getByLabelText(/Precio de venta/i);
    await user.type(priceField, "0");

    await user.click(
      screen.getByRole("button", { name: /guardar|crear producto|agregar producto/i }),
    );

    await waitFor(() => {
      expect(postCalled).toBe(false);
    });

    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("precio negativo → NO invoca POST, campo con aria-invalid='true'", async () => {
    const user = userEvent.setup();
    let postCalled = false;

    server.use(
      http.post("/api/v1/catalog/products", () => {
        postCalled = true;
        return HttpResponse.json({}, { status: 201 });
      }),
    );

    renderCatalog(["/catalog/new"]);

    const nameField = await screen.findByLabelText(/Nombre/i);
    await user.type(nameField, "Producto Test");

    const priceField = screen.getByLabelText(/Precio de venta/i);
    await user.type(priceField, "-100");

    await user.click(
      screen.getByRole("button", { name: /guardar|crear producto|agregar producto/i }),
    );

    await waitFor(() => {
      expect(postCalled).toBe(false);
    });

    expect(screen.getByLabelText(/Precio de venta/i)).toHaveAttribute("aria-invalid", "true");
  });
});

// ── R-07: Alta exitosa ────────────────────────────────────────────────────────

describe("R-07: Alta exitosa de producto", () => {
  it("botón deshabilitado durante petición y navega a /catalog tras POST 201", async () => {
    const user = userEvent.setup();
    let resolvePost!: () => void;
    const pendingPost = new Promise<void>((resolve) => {
      resolvePost = resolve;
    });

    server.use(
      http.post("/api/v1/catalog/products", async () => {
        await pendingPost;
        return HttpResponse.json({ ...DEFAULT_PRODUCT_1, name: "Nuevo Producto" }, { status: 201 });
      }),
    );

    const { router } = renderCatalog(["/catalog/new"]);

    const nameField = await screen.findByLabelText(/Nombre/i);
    await user.type(nameField, "Nuevo Producto");

    const priceField = screen.getByLabelText(/Precio de venta/i);
    await user.type(priceField, "1500.00");

    const submitButton = screen.getByRole("button", {
      name: /guardar|crear producto|agregar producto/i,
    });
    await user.click(submitButton);

    // aria-busy="true" or disabled during request
    await waitFor(() => {
      expect(
        submitButton.hasAttribute("disabled") || submitButton.getAttribute("aria-busy") === "true",
      ).toBe(true);
    });

    resolvePost();

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/catalog");
    });
  });
});

// ── R-08: Conflicto de SKU (409) ──────────────────────────────────────────────

describe("R-08: Error HTTP 409 en alta — Conflicto de SKU", () => {
  it("formulario permanece visible con role='alert' de código SKU duplicado", async () => {
    const user = userEvent.setup();

    server.use(
      http.post("/api/v1/catalog/products", () => {
        return HttpResponse.json(
          {
            code: "DUPLICATE_SKU",
            message: "El código SKU ya está registrado en este negocio.",
            details: null,
          },
          { status: 409 },
        );
      }),
    );

    renderCatalog(["/catalog/new"]);

    const nameField = await screen.findByLabelText(/Nombre/i);
    await user.type(nameField, "Producto Duplicado");

    const priceField = screen.getByLabelText(/Precio de venta/i);
    await user.type(priceField, "1000.00");

    const skuField = screen.queryByLabelText(/código|SKU/i);
    if (skuField) {
      await user.type(skuField, "EXISTENTE-001");
    }

    await user.click(
      screen.getByRole("button", { name: /guardar|crear producto|agregar producto/i }),
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toBeInTheDocument();

    // Form remains visible with its fields
    expect(screen.getByLabelText(/Nombre/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Nombre/i)).toHaveValue("Producto Duplicado");
  });
});

// ── R-09: Validación de servidor (422) ────────────────────────────────────────

describe("R-09: Error HTTP 422 en alta — Validación de servidor", () => {
  it("muestra ErrorResponse.message del servidor en role='alert'", async () => {
    const user = userEvent.setup();
    const serverMessage = "El precio de venta excede el máximo permitido.";

    server.use(
      http.post("/api/v1/catalog/products", () => {
        return HttpResponse.json(
          { code: "VALIDATION_ERROR", message: serverMessage, details: null },
          { status: 422 },
        );
      }),
    );

    renderCatalog(["/catalog/new"]);

    await user.type(await screen.findByLabelText(/Nombre/i), "Producto Test");
    await user.type(screen.getByLabelText(/Precio de venta/i), "9999999999");

    await user.click(
      screen.getByRole("button", { name: /guardar|crear producto|agregar producto/i }),
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(serverMessage);
  });
});
