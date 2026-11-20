import { fireEvent, render, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";

import { Providers } from "@/app/providers";
import { DailyReportPage } from "@/features/reports/pages/DailyReportPage";
import { server } from "@/test/mocks/server";

function renderDailyReportPage(initialEntry = "/reports/daily") {
  const router = createMemoryRouter(
    [
      {
        path: "/reports/daily",
        element: <DailyReportPage />,
      },
    ],
    { initialEntries: [initialEntry] },
  );

  return render(
    <Providers>
      <RouterProvider router={router} />
    </Providers>,
  );
}

describe("DailyReportPage — Integración Design-Blind contra MSW", () => {
  it("Scenario: Initial load omits date query parameter and syncs resolved business local date", async () => {
    const requestedUrls: string[] = [];

    server.use(
      http.get("/api/v1/reports/daily", ({ request }) => {
        requestedUrls.push(request.url);
        return HttpResponse.json({
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
      }),
    );

    renderDailyReportPage("/reports/daily");

    expect(screen.getByRole("status")).toHaveTextContent("Cargando reporte diario...");

    expect(await screen.findByText("$30.000,00")).toBeInTheDocument();

    expect(requestedUrls).toHaveLength(1);
    const firstRequestUrl = new URL(requestedUrls[0] ?? "http://localhost");
    expect(firstRequestUrl.pathname).toBe("/api/v1/reports/daily");
    expect(firstRequestUrl.searchParams.has("date")).toBe(false);

    const dateInput = screen.getByLabelText("Fecha del reporte");
    expect(dateInput).toHaveValue("2026-11-19");
    expect(screen.getByText(/America\/Argentina\/Buenos_Aires/)).toBeInTheDocument();
  });

  it("Scenario: Owner views daily report with sales and positive gross margin (state: ready) & Scenario: Payment method breakdown renders amounts and proportions for all three methods", async () => {
    renderDailyReportPage("/reports/daily");

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Reporte Diario de Ventas y Margen",
      }),
    ).toBeInTheDocument();

    expect(await screen.findByText("$30.000,00")).toBeInTheDocument();
    expect(screen.getByText("$9.000,00")).toBeInTheDocument();
    expect(screen.getByText(/30\.00%/)).toBeInTheDocument();
    expect(screen.getByText("$21.000,00")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();

    const cashRow = screen.getByRole("row", { name: /Efectivo/i });
    expect(within(cashRow).getByText("$15.000,00")).toBeInTheDocument();
    expect(within(cashRow).getByText("50.00%")).toBeInTheDocument();

    const cardRow = screen.getByRole("row", { name: /Tarjeta/i });
    expect(within(cardRow).getByText("$10.000,00")).toBeInTheDocument();
    expect(within(cardRow).getByText("33.33%")).toBeInTheDocument();

    const transferRow = screen.getByRole("row", { name: /Transferencia/i });
    expect(within(transferRow).getByText("$5.000,00")).toBeInTheDocument();
    expect(within(transferRow).getByText("16.67%")).toBeInTheDocument();
  });

  it("Scenario: Selecting a new date triggers a report query for that date", async () => {
    const requestedDates: Array<string | null> = [];

    server.use(
      http.get("/api/v1/reports/daily", ({ request }) => {
        const url = new URL(request.url);
        const dateParam = url.searchParams.get("date");
        requestedDates.push(dateParam);

        if (dateParam === "2026-11-18") {
          return HttpResponse.json({
            date: "2026-11-18",
            timezone: "America/Argentina/Buenos_Aires",
            total_sales: "12000.00",
            transactions_count: 2,
            total_cost: "8000.00",
            gross_margin: "4000.00",
            margin_percentage: "33.33",
            payment_breakdown: {
              cash: "12000.00",
              card: "0.00",
              transfer: "0.00",
            },
          });
        }

        return HttpResponse.json({
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
      }),
    );

    renderDailyReportPage("/reports/daily");

    expect(await screen.findByText("$30.000,00")).toBeInTheDocument();

    const dateInput = screen.getByLabelText("Fecha del reporte");
    fireEvent.change(dateInput, { target: { value: "2026-11-18" } });

    const kpiRegion = await screen.findByRole("region", {
      name: "Indicadores clave del día",
    });
    expect(within(kpiRegion).getByText("$12.000,00")).toBeInTheDocument();
    const cashRow = screen.getByRole("row", { name: /Efectivo/i });
    expect(within(cashRow).getByText("$12.000,00")).toBeInTheDocument();
    expect(screen.getByText("$4.000,00")).toBeInTheDocument();
    expect(screen.getByText("$8.000,00")).toBeInTheDocument();
    expect(dateInput).toHaveValue("2026-11-18");
    expect(requestedDates).toEqual([null, "2026-11-18"]);
  });

  it("Scenario: Day without sales displays empty state notice and zero KPIs (state: empty)", async () => {
    server.use(
      http.get("/api/v1/reports/daily", () => {
        return HttpResponse.json({
          date: "2026-11-19",
          timezone: "America/Argentina/Buenos_Aires",
          total_sales: "0.00",
          transactions_count: 0,
          total_cost: "0.00",
          gross_margin: "0.00",
          margin_percentage: "0.00",
          payment_breakdown: {
            cash: "0.00",
            card: "0.00",
            transfer: "0.00",
          },
        });
      }),
    );

    renderDailyReportPage("/reports/daily");

    expect(
      await screen.findByText("Sin ventas registradas en la fecha seleccionada"),
    ).toBeInTheDocument();

    expect(screen.getAllByText("$0,00").length).toBeGreaterThanOrEqual(6);
    expect(screen.getAllByText(/0\.00%/).length).toBeGreaterThanOrEqual(4);
    expect(screen.queryByText(/NaN/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/null/i)).not.toBeInTheDocument();
  });

  it("Scenario: API error displays accessible alert with server message and retry action recovers (state: error)", async () => {
    let attemptCount = 0;

    server.use(
      http.get("/api/v1/reports/daily", () => {
        attemptCount += 1;
        if (attemptCount === 1) {
          return HttpResponse.json(
            {
              code: "FORBIDDEN",
              message: "Solo el dueño del comercio puede consultar reportes",
              details: null,
            },
            { status: 403 },
          );
        }

        return HttpResponse.json({
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
      }),
    );

    renderDailyReportPage("/reports/daily");

    const alertRegion = await screen.findByRole("alert");
    expect(alertRegion).toHaveTextContent("Solo el dueño del comercio puede consultar reportes");

    const retryButton = screen.getByRole("button", { name: "Reintentar" });
    fireEvent.click(retryButton);

    expect(await screen.findByText("$30.000,00")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
