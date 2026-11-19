import { http, HttpResponse } from "msw";

const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export const handlers = [
  // Handler base para health check
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
];
