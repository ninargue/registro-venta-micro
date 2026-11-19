import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DailyReportView } from "@/features/reports/components/DailyReportView";
import type { DailyReportResponse } from "@/features/reports/types/reports.types";

const READY_REPORT_FIXTURE: DailyReportResponse = {
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
};

const NEGATIVE_MARGIN_FIXTURE: DailyReportResponse = {
  date: "2026-11-19",
  timezone: "America/Argentina/Buenos_Aires",
  total_sales: "1000.00",
  transactions_count: 1,
  total_cost: "1250.00",
  gross_margin: "-250.00",
  margin_percentage: "-25.00",
  payment_breakdown: {
    cash: "1000.00",
    card: "0.00",
    transfer: "0.00",
  },
};

const EMPTY_REPORT_FIXTURE: DailyReportResponse = {
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
};

describe("DailyReportView — Catálogo ejecutable por estado y accesibilidad Design-Blind", () => {
  it("Scenario: Loading indicator is announced while daily report request is pending (state: loading)", () => {
    render(
      <DailyReportView status="loading" selectedDate="" onDateChange={vi.fn()} onRetry={vi.fn()} />,
    );

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Reporte Diario de Ventas y Margen",
      }),
    ).toBeInTheDocument();

    const statusIndicator = screen.getByRole("status");
    expect(statusIndicator).toHaveTextContent("Cargando reporte diario...");
  });

  it("Scenario: Owner views daily report with sales and positive gross margin (state: ready)", () => {
    render(
      <DailyReportView
        status="ready"
        report={READY_REPORT_FIXTURE}
        selectedDate="2026-11-19"
        onDateChange={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Reporte Diario de Ventas y Margen",
      }),
    ).toBeInTheDocument();

    const dateInput = screen.getByLabelText("Fecha del reporte");
    expect(dateInput).toHaveValue("2026-11-19");
    expect(screen.getByText(/America\/Argentina\/Buenos_Aires/)).toBeInTheDocument();

    expect(screen.getByText("Ventas Totales")).toBeInTheDocument();
    expect(screen.getByText("$30.000,00")).toBeInTheDocument();

    expect(screen.getByText("Margen Bruto")).toBeInTheDocument();
    expect(screen.getByText("$9.000,00")).toBeInTheDocument();
    expect(screen.getByText(/30\.00%/)).toBeInTheDocument();

    expect(screen.getByText("Costo Mercadería")).toBeInTheDocument();
    expect(screen.getByText("$21.000,00")).toBeInTheDocument();

    expect(screen.getByText("Tickets")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("Scenario: Owner views daily report with negative gross margin (state: ready)", () => {
    render(
      <DailyReportView
        status="ready"
        report={NEGATIVE_MARGIN_FIXTURE}
        selectedDate="2026-11-19"
        onDateChange={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText("Margen Bruto")).toBeInTheDocument();
    expect(screen.getByText("-$250,00")).toBeInTheDocument();
    expect(screen.getByText(/-25\.00%/)).toBeInTheDocument();
  });

  it("Scenario: Payment method breakdown renders amounts and proportions for all three methods", () => {
    render(
      <DailyReportView
        status="ready"
        report={READY_REPORT_FIXTURE}
        selectedDate="2026-11-19"
        onDateChange={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "Desglose por Medio de Pago" })).toBeInTheDocument();

    const table = screen.getByRole("table");
    const cashRow = screen.getByRole("row", { name: /Efectivo/i });
    expect(within(cashRow).getByText("$15.000,00")).toBeInTheDocument();
    expect(within(cashRow).getByText("50.00%")).toBeInTheDocument();

    const cardRow = screen.getByRole("row", { name: /Tarjeta/i });
    expect(within(cardRow).getByText("$10.000,00")).toBeInTheDocument();
    expect(within(cardRow).getByText("33.33%")).toBeInTheDocument();

    const transferRow = screen.getByRole("row", { name: /Transferencia/i });
    expect(within(transferRow).getByText("$5.000,00")).toBeInTheDocument();
    expect(within(transferRow).getByText("16.67%")).toBeInTheDocument();

    expect(table).toBeInTheDocument();
  });

  it("Scenario: Day without sales displays empty state notice and zero KPIs (state: empty)", () => {
    render(
      <DailyReportView
        status="empty"
        report={EMPTY_REPORT_FIXTURE}
        selectedDate="2026-11-19"
        onDateChange={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText("Sin ventas registradas en la fecha seleccionada")).toBeInTheDocument();

    expect(screen.getByText("Ventas Totales")).toBeInTheDocument();
    expect(screen.getByText("Margen Bruto")).toBeInTheDocument();
    expect(screen.getByText("Costo Mercadería")).toBeInTheDocument();
    expect(screen.getByText("Tickets")).toBeInTheDocument();

    expect(screen.getAllByText("$0,00").length).toBeGreaterThanOrEqual(6);
    expect(screen.getAllByText(/0\.00%/).length).toBeGreaterThanOrEqual(4);
    expect(screen.getByText("0")).toBeInTheDocument();

    expect(screen.queryByText(/NaN/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/null/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Infinity/i)).not.toBeInTheDocument();
  });

  it("Scenario: API error displays accessible alert with server message and retry action recovers (state: error)", () => {
    const onRetry = vi.fn();

    render(
      <DailyReportView
        status="error"
        errorMessage="Solo el dueño del comercio puede consultar reportes"
        selectedDate="2026-11-19"
        onDateChange={vi.fn()}
        onRetry={onRetry}
      />,
    );

    const alertRegion = screen.getByRole("alert");
    expect(alertRegion).toHaveTextContent("Solo el dueño del comercio puede consultar reportes");

    const retryButton = screen.getByRole("button", { name: "Reintentar" });
    fireEvent.click(retryButton);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
