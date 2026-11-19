import { describe, expect, it } from "vitest";

describe("MSW mock server (server.ts)", () => {
  it("intercepta peticiones GET a /api/v1/health y responde json healthy", async () => {
    const response = await fetch("/api/v1/health");
    expect(response.status).toBe(200);

    const body = (await response.json()) as { status: string };
    expect(body).toEqual({ status: "healthy" });
  });

  it("intercepta GET /api/v1/reports/daily alineado con DailyReportResponse y valida date", async () => {
    const defaultResponse = await fetch("/api/v1/reports/daily");
    expect(defaultResponse.status).toBe(200);

    const defaultBody = (await defaultResponse.json()) as {
      date: string;
      timezone: string;
      total_sales: string;
      transactions_count: number;
      total_cost: string;
      gross_margin: string;
      margin_percentage: string;
      payment_breakdown: { cash: string; card: string; transfer: string };
    };
    expect(defaultBody).toEqual({
      date: "2026-11-19",
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

    const invalidDateResponse = await fetch("/api/v1/reports/daily?date=invalid-date");
    expect(invalidDateResponse.status).toBe(422);
    const errorBody = (await invalidDateResponse.json()) as {
      code: string;
      message: string;
    };
    expect(errorBody.code).toBe("VALIDATION_ERROR");
  });
});
