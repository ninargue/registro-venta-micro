import { http, HttpResponse } from "msw";

const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
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

export const handlers = [
  http.get("/api/v1/health", () => {
    return HttpResponse.json({ status: "healthy" });
  }),

  // Handler base para GET /api/v1/reports/daily (DailyReportResponse / ErrorResponse)
  http.get("/api/v1/reports/daily", ({ request }) => {
    const url = new URL(request.url);
    const requestedDate = url.searchParams.get("date");

    if (requestedDate !== null && !ISO_DATE_PATTERN.test(requestedDate)) {
      return HttpResponse.json(
        {
          code: "VALIDATION_ERROR",
          message: "El formato de fecha debe ser YYYY-MM-DD",
          details: null,
        },
        { status: 422 },
      );
    }

    const resolvedDate = requestedDate ?? "2026-11-19";

    return HttpResponse.json({
      date: resolvedDate,
      timezone: "America/Argentina/Buenos_Aires",
      total_sales: "30000.00",
      transactions_count: 3,
      total_cost: "21000.00",
      gross_margin: "9000.00",
      margin_percentage: "30.00",
      payment_breakdown: {
        cash: "15000.00",
        card: "10000.00",
        transfer: "5000.00",
      },
    });
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
];
