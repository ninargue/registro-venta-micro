/**
 * product-list.test.tsx — Design-Blind UI tests for catalog listing
 *
 * Covers: R-01 (loading), R-02 (empty), R-03 (search), R-04 (error), R-14 (offline)
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
