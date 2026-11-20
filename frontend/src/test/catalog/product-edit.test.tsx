/**
 * product-edit.test.tsx — Design-Blind UI tests for product editing
 *
 * Covers: R-10 (access edit form), R-11 (success), R-12 (404 not found),
 *         R-13 (cancel from both create and edit forms)
 * Each test maps 1:1 to a Given/When/Then scenario in:
 *   openspec/changes/issue-44-catalogo-productos-frontend/specs/catalog-admin/spec.md
 *
 * Selector rules: ONLY semantic/accessible selectors (getByRole, getByLabelText,
 * getByText, findByRole). NO CSS class selectors. NO data-testid.
 */

import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import type { RouteObject } from "react-router";
import { describe, expect, it } from "vitest";
import { Providers } from "@/app/providers";
import { CatalogListContainer } from "@/features/catalog/containers/CatalogListContainer";
import { ProductCreateContainer } from "@/features/catalog/containers/ProductCreateContainer";
import { ProductEditContainer } from "@/features/catalog/containers/ProductEditContainer";
import { DEFAULT_PRODUCT_1, DEFAULT_TEST_BUSINESS, DEFAULT_TEST_USER } from "@/test/mocks/handlers";
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

// ── R-10: Acceso al formulario de edición ─────────────────────────────────────

describe("R-10: Acceso al formulario de edición de producto", () => {
  it("botón 'Editar <nombre>' navega a /catalog/:id/edit con formulario pre-cargado", async () => {
    const user = userEvent.setup();
    const { router } = renderCatalog();

    await screen.findByRole("heading", { name: /Catálogo de productos/i });
    await screen.findByText(DEFAULT_PRODUCT_1.name);

    const editButton = screen.getByRole("button", {
      name: new RegExp(`Editar ${DEFAULT_PRODUCT_1.name}`, "i"),
    });
    await user.click(editButton);

    await waitFor(() => {
      expect(router.state.location.pathname).toMatch(/\/catalog\/.+\/edit$/);
    });

    // Form pre-loaded with product data
    const nameField = await screen.findByLabelText(/Nombre/i);
    expect(nameField).toHaveValue(DEFAULT_PRODUCT_1.name);

    const priceField = screen.getByLabelText(/Precio de venta/i);
    expect(priceField).toHaveValue(DEFAULT_PRODUCT_1.sale_price);
  });
});

// ── R-11: Edición exitosa ─────────────────────────────────────────────────────

describe("R-11: Edición exitosa de producto", () => {
  it("botón deshabilitado durante petición y navega a /catalog tras PATCH 200", async () => {
    const user = userEvent.setup();
    let resolvePatch!: () => void;
    const pendingPatch = new Promise<void>((resolve) => {
      resolvePatch = resolve;
    });

    server.use(
      http.patch("/api/v1/catalog/products/:product_id", async () => {
        await pendingPatch;
        return HttpResponse.json({ ...DEFAULT_PRODUCT_1, name: "Nombre Editado" });
      }),
    );

    const { router } = renderCatalog([`/catalog/${DEFAULT_PRODUCT_1.id}/edit`]);

    const nameField = await screen.findByLabelText(/Nombre/i);
    await user.clear(nameField);
    await user.type(nameField, "Nombre Editado");

    const submitButton = screen.getByRole("button", {
      name: /guardar|actualizar|editar producto/i,
    });
    await user.click(submitButton);

    // Disabled or aria-busy during request
    await waitFor(() => {
      expect(
        submitButton.hasAttribute("disabled") || submitButton.getAttribute("aria-busy") === "true",
      ).toBe(true);
    });

    resolvePatch();

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/catalog");
    });
  });
});

// ── R-12: Producto no encontrado (404) ────────────────────────────────────────

describe("R-12: Error HTTP 404 en edición — Producto no encontrado", () => {
  it("muestra mensaje observable de no encontrado con acción para volver al catálogo", async () => {
    const user = userEvent.setup();

    server.use(
      http.patch("/api/v1/catalog/products/:product_id", () => {
        return HttpResponse.json(
          {
            code: "PRODUCT_NOT_FOUND",
            message: "El producto no fue encontrado.",
            details: null,
          },
          { status: 404 },
        );
      }),
    );

    renderCatalog([`/catalog/${DEFAULT_PRODUCT_1.id}/edit`]);

    const nameField = await screen.findByLabelText(/Nombre/i);
    await user.clear(nameField);
    await user.type(nameField, "Nombre Nuevo");

    await user.click(screen.getByRole("button", { name: /guardar|actualizar|editar producto/i }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();

    // Action to go back to catalog
    const backAction =
      screen.queryByRole("link", { name: /volver al catálogo/i }) ??
      screen.queryByRole("button", { name: /volver al catálogo/i });
    expect(backAction).toBeInTheDocument();
  });
});

// ── R-13: Cancelar formulario ─────────────────────────────────────────────────

describe("R-13: Cancelar formulario", () => {
  it("Cancelar en /catalog/new navega a /catalog sin invocar POST", async () => {
    const user = userEvent.setup();
    let postCalled = false;

    server.use(
      http.post("/api/v1/catalog/products", () => {
        postCalled = true;
        return HttpResponse.json({}, { status: 201 });
      }),
    );

    const { router } = renderCatalog(["/catalog/new"]);

    await screen.findByLabelText(/Nombre/i);

    const cancelButton = screen.getByRole("button", { name: /cancelar/i });
    await user.click(cancelButton);

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/catalog");
    });

    expect(postCalled).toBe(false);
  });

  it("Cancelar en /catalog/:id/edit navega a /catalog sin invocar PATCH", async () => {
    const user = userEvent.setup();
    let patchCalled = false;

    server.use(
      http.patch("/api/v1/catalog/products/:product_id", () => {
        patchCalled = true;
        return HttpResponse.json({});
      }),
    );

    const { router } = renderCatalog([`/catalog/${DEFAULT_PRODUCT_1.id}/edit`]);

    await screen.findByLabelText(/Nombre/i);

    const cancelButton = screen.getByRole("button", { name: /cancelar/i });
    await user.click(cancelButton);

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/catalog");
    });

    expect(patchCalled).toBe(false);
  });
});
