/**
 * hooks.test.ts — TanStack Query hook tests for the Catalog feature
 *
 * Fase A: Tests are intentionally RED — imported hooks do not exist yet.
 * Uses React.createElement (no JSX) to avoid requiring a .tsx extension.
 *
 * Covers:
 *   useProducts    — query key, fetching, params forwarding, Dexie persistence
 *   useCreateProduct — POST mutation, cache invalidation on success
 *   useUpdateProduct — PATCH mutation, cache invalidation on success
 */

import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
// Fase A: these modules do not exist yet — tests will fail with "Cannot find module"
import { useProducts } from "@/features/catalog/hooks/useProducts";
import { useCreateProduct } from "@/features/catalog/hooks/useCreateProduct";
import { useUpdateProduct } from "@/features/catalog/hooks/useUpdateProduct";
import { db } from "@/lib/db";
import { DEFAULT_PRODUCT_1, DEFAULT_PRODUCT_2 } from "@/test/mocks/handlers";
import { server } from "@/test/mocks/server";

// ── Test wrapper factory ──────────────────────────────────────────────────────

function createTestWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  // No JSX syntax: use React.createElement so this compiles as plain .ts
  function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  }

  return { Wrapper, queryClient };
}

// ── useProducts ───────────────────────────────────────────────────────────────

describe("useProducts", () => {
  it("retorna isLoading=true y luego data con la lista de productos del fixture MSW", async () => {
    const { Wrapper } = createTestWrapper();

    const { result } = renderHook(() => useProducts({}), { wrapper: Wrapper });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data?.items[0]?.name).toBe(DEFAULT_PRODUCT_1.name);
    expect(result.current.data?.total).toBe(2);
  });

  it("pasa el parámetro q en la URL cuando se proporciona en params", async () => {
    const { Wrapper } = createTestWrapper();
    let capturedUrl = "";

    server.use(
      http.get("/api/v1/catalog/products", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          items: [DEFAULT_PRODUCT_1],
          total: 1,
          limit: 50,
          offset: 0,
        });
      }),
    );

    const { result } = renderHook(() => useProducts({ q: "Yerba" }), { wrapper: Wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(capturedUrl).toContain("q=Yerba");
  });

  it("retorna isError=true y data=undefined ante error de red", async () => {
    const { Wrapper } = createTestWrapper();

    server.use(
      http.get("/api/v1/catalog/products", () => {
        return HttpResponse.error();
      }),
    );

    const { result } = renderHook(() => useProducts({}), { wrapper: Wrapper });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.data).toBeUndefined();
  });

  it("omite q de la URL cuando el parámetro está vacío o no se proporciona", async () => {
    const { Wrapper } = createTestWrapper();
    let capturedUrl = "";

    server.use(
      http.get("/api/v1/catalog/products", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          items: [DEFAULT_PRODUCT_1, DEFAULT_PRODUCT_2],
          total: 2,
          limit: 50,
          offset: 0,
        });
      }),
    );

    const { result } = renderHook(() => useProducts({ q: "" }), { wrapper: Wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(capturedUrl).not.toContain("q=");
  });
});

// ── useCreateProduct ──────────────────────────────────────────────────────────

describe("useCreateProduct", () => {
  it("invoca POST /api/v1/catalog/products e invalida la query ['catalog','products'] en éxito", async () => {
    const { Wrapper, queryClient } = createTestWrapper();
    let postBody: unknown = null;

    server.use(
      http.post("/api/v1/catalog/products", async ({ request }) => {
        postBody = await request.json();
        return HttpResponse.json(
          {
            ...DEFAULT_PRODUCT_1,
            name: "Nuevo Producto",
            sale_price: "2000.00",
          },
          { status: 201 },
        );
      }),
    );

    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateProduct(), { wrapper: Wrapper });

    result.current.mutate({
      name: "Nuevo Producto",
      sale_price: "2000.00",
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Verify POST body was sent
    expect((postBody as Record<string, unknown>).name).toBe("Nuevo Producto");

    // Verify cache invalidation
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
        queryKey: expect.arrayContaining(["catalog", "products"]),
      }),
    );
  });

  it("expone isError=true con el mensaje del servidor ante POST 409", async () => {
    const { Wrapper } = createTestWrapper();

    server.use(
      http.post("/api/v1/catalog/products", () => {
        return HttpResponse.json(
          {
            code: "DUPLICATE_SKU",
            message: "El código SKU ya está registrado.",
            details: null,
          },
          { status: 409 },
        );
      }),
    );

    const { result } = renderHook(() => useCreateProduct(), { wrapper: Wrapper });

    result.current.mutate({ name: "Producto", sale_price: "1000" });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });

  it("expone isError=true con el mensaje del servidor ante POST 422", async () => {
    const { Wrapper } = createTestWrapper();

    server.use(
      http.post("/api/v1/catalog/products", () => {
        return HttpResponse.json(
          {
            code: "VALIDATION_ERROR",
            message: "Precio inválido.",
            details: null,
          },
          { status: 422 },
        );
      }),
    );

    const { result } = renderHook(() => useCreateProduct(), { wrapper: Wrapper });

    result.current.mutate({ name: "Producto", sale_price: "-1" });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

// ── useUpdateProduct ──────────────────────────────────────────────────────────

describe("useUpdateProduct", () => {
  it("invoca PATCH /api/v1/catalog/products/:id e invalida la query ['catalog','products'] en éxito", async () => {
    const { Wrapper, queryClient } = createTestWrapper();
    let capturedProductId = "";
    let patchBody: unknown = null;

    server.use(
      http.patch("/api/v1/catalog/products/:product_id", async ({ params, request }) => {
        capturedProductId = params.product_id as string;
        patchBody = await request.json();
        return HttpResponse.json({ ...DEFAULT_PRODUCT_1, name: "Nombre Editado" });
      }),
    );

    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useUpdateProduct(), { wrapper: Wrapper });

    result.current.mutate({ id: DEFAULT_PRODUCT_1.id, payload: { name: "Nombre Editado" } });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Correct product ID in URL
    expect(capturedProductId).toBe(DEFAULT_PRODUCT_1.id);

    // Correct body sent
    expect((patchBody as Record<string, unknown>).name).toBe("Nombre Editado");

    // Cache invalidation
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
        queryKey: expect.arrayContaining(["catalog", "products"]),
      }),
    );
  });

  it("expone isError=true ante PATCH 404 producto no encontrado", async () => {
    const { Wrapper } = createTestWrapper();

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

    const { result } = renderHook(() => useUpdateProduct(), { wrapper: Wrapper });

    result.current.mutate({ id: DEFAULT_PRODUCT_1.id, payload: { name: "Editado" } });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

// ── Brechas de mutation testing (M05, M10) ───────────────────────────────────

describe("useProducts — consistencia de clave y persistencia offline", () => {
  it("registra la query bajo ['catalog','products'] (la misma que invalidan las mutations)", async () => {
    const { Wrapper, queryClient } = createTestWrapper();
    const { result } = renderHook(() => useProducts({}), { wrapper: Wrapper });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(queryClient.getQueryCache().findAll({ queryKey: ["catalog", "products"] })).toHaveLength(
      1,
    );
  });

  it("persiste los items en Dexie con bulkPut tras un fetch exitoso", async () => {
    const bulkPutSpy = vi.spyOn(db.products, "bulkPut").mockResolvedValue("");
    const { Wrapper } = createTestWrapper();
    const { result } = renderHook(() => useProducts({}), { wrapper: Wrapper });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(bulkPutSpy).toHaveBeenCalledWith(result.current.data?.items);
    bulkPutSpy.mockRestore();
  });
});
