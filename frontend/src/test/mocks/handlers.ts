import { http, HttpResponse } from "msw";

export const DEFAULT_TEST_USER = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "dueno@negocio.com",
} as const;

export const DEFAULT_TEST_BUSINESS = {
  id: "22222222-2222-4222-8222-222222222222",
  name: "Kiosco Central",
  country: "AR",
  timezone: "America/Argentina/Buenos_Aires",
  role: "owner" as const,
};

// ── Catalog fixtures ──────────────────────────────────────────────────────────

export const DEFAULT_PRODUCT_1 = {
  id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  code: "YM-001",
  name: "Yerba Mate 1kg",
  sale_price: "3500.50",
  cost_price: "2800.00",
  stock: "10.00",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
} as const;

export const DEFAULT_PRODUCT_2 = {
  id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  code: "AZ-002",
  name: "Azúcar 1kg",
  sale_price: "1200.00",
  cost_price: null,
  stock: "5.00",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
} as const;

export const handlers = [
  http.get("/api/v1/health", () => {
    return HttpResponse.json({ status: "healthy" });
  }),

  http.get("/api/v1/auth/me", () => {
    return HttpResponse.json(
      {
        code: "UNAUTHENTICATED",
        message: "No autenticado",
        details: null,
      },
      { status: 401 },
    );
  }),

  http.post("/api/v1/auth/refresh", () => {
    return HttpResponse.json(
      {
        code: "UNAUTHENTICATED",
        message: "Sesión expirada",
        details: null,
      },
      { status: 401 },
    );
  }),

  http.post("/api/v1/auth/login", () => {
    return HttpResponse.json({
      user: DEFAULT_TEST_USER,
      requires_onboarding: false,
      business: DEFAULT_TEST_BUSINESS,
    });
  }),

  http.post("/api/v1/auth/onboarding", () => {
    return HttpResponse.json(
      {
        ...DEFAULT_TEST_BUSINESS,
        created_at: "2026-01-01T00:00:00Z",
      },
      { status: 201 },
    );
  }),

  http.post("/api/v1/auth/logout", () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // ── Catalog handlers (defaults; override per-test with server.use) ──────────

  http.get("/api/v1/catalog/products", () => {
    return HttpResponse.json({
      items: [DEFAULT_PRODUCT_1, DEFAULT_PRODUCT_2],
      total: 2,
      limit: 50,
      offset: 0,
    });
  }),

  http.post("/api/v1/catalog/products", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        code: (body.code as string | null) ?? null,
        name: body.name as string,
        sale_price: String(body.sale_price),
        cost_price: body.cost_price ? String(body.cost_price) : null,
        stock: body.stock ? String(body.stock) : "0.00",
        is_active: true,
        created_at: "2026-11-19T00:00:00Z",
        updated_at: "2026-11-19T00:00:00Z",
      },
      { status: 201 },
    );
  }),

  http.patch("/api/v1/catalog/products/:product_id", async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      id: params.product_id as string,
      code: DEFAULT_PRODUCT_1.code,
      name: (body.name as string | undefined) ?? DEFAULT_PRODUCT_1.name,
      sale_price: body.sale_price ? String(body.sale_price) : DEFAULT_PRODUCT_1.sale_price,
      cost_price: DEFAULT_PRODUCT_1.cost_price,
      stock: DEFAULT_PRODUCT_1.stock,
      is_active: true,
      created_at: DEFAULT_PRODUCT_1.created_at,
      updated_at: "2026-11-19T00:00:00Z",
    });
  }),
];
