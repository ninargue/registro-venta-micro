/**
 * catalog.test.tsx — Design-Blind UI tests for the Catalog feature
 *
 * Fase A: Tests are intentionally RED — imported containers do not exist yet.
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
import { afterEach, describe, expect, it } from "vitest";
import { Providers } from "@/app/providers";
// Fase A: these modules do not exist yet — tests will fail with "Cannot find module"
import { CatalogListContainer } from "@/features/catalog/containers/CatalogListContainer";
import { ProductCreateContainer } from "@/features/catalog/containers/ProductCreateContainer";
import { ProductEditContainer } from "@/features/catalog/containers/ProductEditContainer";
import {
  DEFAULT_PRODUCT_1,
  DEFAULT_PRODUCT_2,
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

// ── R-01: Lista de productos con estado de carga ───────────────────────────────

describe("R-01: Lista de productos con estado de carga", () => {
  it("muestra indicador de carga accesible (aria-busy o role=status) mientras resuelve", async () => {
    let resolveProducts!: () => void;
    const pendingProducts = new Promise<void>((resolve) => {
      resolveProducts = resolve;
    });

    server.use(
      http.get("/api/v1/catalog/products", async () => {
        await pendingProducts;
        return HttpResponse.json({
          items: [DEFAULT_PRODUCT_1],
          total: 1,
          limit: 50,
          offset: 0,
        });
      }),
    );

    renderCatalog();

    // Loading indicator must be accessible
    await waitFor(() => {
      const statusEl = screen.queryByRole("status");
      const progressEl = screen.queryByRole("progressbar");
      const busyEl = document.querySelector('[aria-busy="true"]');
      expect(statusEl ?? progressEl ?? busyEl).not.toBeNull();
    });

    resolveProducts();

    // After data loads: heading and product data are visible
    await screen.findByRole("heading", { name: /Catálogo de productos/i });
  });

  it("muestra el heading 'Catálogo de productos' y datos de cada producto al resolver", async () => {
    renderCatalog();

    await screen.findByRole("heading", { name: /Catálogo de productos/i });

    expect(await screen.findByText(DEFAULT_PRODUCT_1.name)).toBeInTheDocument();
    expect(screen.getByText(DEFAULT_PRODUCT_1.sale_price)).toBeInTheDocument();
    expect(screen.getByText(DEFAULT_PRODUCT_1.stock)).toBeInTheDocument();

    expect(screen.getByText(DEFAULT_PRODUCT_2.name)).toBeInTheDocument();
    expect(screen.getByText(DEFAULT_PRODUCT_2.sale_price)).toBeInTheDocument();
  });
});

// ── R-02: Lista vacía ─────────────────────────────────────────────────────────

describe("R-02: Lista vacía", () => {
  it("muestra mensaje observable de vacío y acción para agregar el primer producto", async () => {
    server.use(
      http.get("/api/v1/catalog/products", () => {
        return HttpResponse.json({ items: [], total: 0, limit: 50, offset: 0 });
      }),
    );

    renderCatalog();

    // Empty state text
    expect(await screen.findByText(/no hay productos/i)).toBeInTheDocument();

    // Action to add product
    expect(screen.getByRole("button", { name: /agregar producto/i })).toBeInTheDocument();
  });
});

// ── R-03: Búsqueda reactiva ───────────────────────────────────────────────────

describe("R-03: Búsqueda reactiva por texto", () => {
  it("escribir en 'Buscar producto' dispara GET con q=<texto> tras debounce", async () => {
    const user = userEvent.setup({ delay: null });
    const capturedUrls: string[] = [];

    server.use(
      http.get("/api/v1/catalog/products", ({ request }) => {
        capturedUrls.push(request.url);
        const url = new URL(request.url);
        const q = url.searchParams.get("q");
        const items = q ? [DEFAULT_PRODUCT_1] : [DEFAULT_PRODUCT_1, DEFAULT_PRODUCT_2];
        return HttpResponse.json({ items, total: items.length, limit: 50, offset: 0 });
      }),
    );

    renderCatalog();

    const searchInput = await screen.findByLabelText(/Buscar producto/i);
    await user.type(searchInput, "Yerba");

    // After debounce (~300ms), query with q= should have been issued
    await waitFor(
      () => {
        expect(capturedUrls.some((u) => u.includes("q=Yerba") || u.includes("q="))).toBe(true);
      },
      { timeout: 1500 },
    );

    expect(await screen.findByText(DEFAULT_PRODUCT_1.name)).toBeInTheDocument();
  });

  it("borrar el buscador dispara GET sin q y muestra catálogo completo", async () => {
    const user = userEvent.setup({ delay: null });
    const capturedUrls: string[] = [];

    server.use(
      http.get("/api/v1/catalog/products", ({ request }) => {
        capturedUrls.push(request.url);
        const url = new URL(request.url);
        const q = url.searchParams.get("q");
        const items = q ? [DEFAULT_PRODUCT_1] : [DEFAULT_PRODUCT_1, DEFAULT_PRODUCT_2];
        return HttpResponse.json({ items, total: items.length, limit: 50, offset: 0 });
      }),
    );

    renderCatalog();

    const searchInput = await screen.findByLabelText(/Buscar producto/i);
    await user.type(searchInput, "Yerba");

    await waitFor(
      () => {
        expect(capturedUrls.some((u) => u.includes("q="))).toBe(true);
      },
      { timeout: 1500 },
    );

    await user.clear(searchInput);

    // After clearing, all products visible again
    await waitFor(
      () => {
        expect(screen.queryByText(DEFAULT_PRODUCT_2.name)).toBeInTheDocument();
      },
      { timeout: 1500 },
    );
  });
});

// ── R-04: Error de red ────────────────────────────────────────────────────────

describe("R-04: Error de red o servidor en listado", () => {
  it("muestra role='alert' con mensaje de error y acción de reintento ante error de red", async () => {
    server.use(
      http.get("/api/v1/catalog/products", () => {
        return HttpResponse.error();
      }),
    );

    renderCatalog();

    const alert = await screen.findByRole("alert");
    expect(alert).toBeInTheDocument();

    // Retry action
    expect(screen.getByRole("button", { name: /reintentar/i })).toBeInTheDocument();
  });

  it("muestra role='alert' ante HTTP 500 con acción de reintento", async () => {
    server.use(
      http.get("/api/v1/catalog/products", () => {
        return HttpResponse.json(
          { code: "INTERNAL_ERROR", message: "Error interno del servidor.", details: null },
          { status: 500 },
        );
      }),
    );

    renderCatalog();

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reintentar/i })).toBeInTheDocument();
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

// ── R-14: Modo offline ────────────────────────────────────────────────────────

describe("R-14: Modo offline — lista servida desde caché Dexie", () => {
  afterEach(() => {
    // Restore navigator.onLine
    Object.defineProperty(window.navigator, "onLine", {
      get: () => true,
      configurable: true,
    });
    window.dispatchEvent(new Event("online"));
  });

  it("muestra aviso de modo sin conexión y deshabilita botones de alta/edición", async () => {
    // Simulate going offline
    Object.defineProperty(window.navigator, "onLine", {
      get: () => false,
      configurable: true,
    });
    window.dispatchEvent(new Event("offline"));

    // Network calls will fail (simulating no connectivity)
    server.use(
      http.get("/api/v1/catalog/products", () => {
        return HttpResponse.error();
      }),
    );

    renderCatalog();

    // Offline notice
    const offlineNotice = await screen.findByText(/Mostrando datos guardados|sin conexión/i);
    expect(offlineNotice).toBeInTheDocument();
    expect(await screen.findByRole("status")).toHaveTextContent(
      /Mostrando datos guardados|sin conexión/i,
    );

    // Add button disabled in offline mode
    const addButton = screen.queryByRole("button", {
      name: /agregar producto|nuevo producto/i,
    });
    if (addButton) {
      expect(addButton).toBeDisabled();
    }
  });
});
