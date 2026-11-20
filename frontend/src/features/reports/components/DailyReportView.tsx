import { DailyReportDateFilter } from "@/features/reports/components/DailyReportDateFilter";
import { DailyReportKpiGrid } from "@/features/reports/components/DailyReportKpiGrid";
import { PaymentBreakdownTable } from "@/features/reports/components/PaymentBreakdownTable";
import type { DailyReportResponse } from "@/features/reports/types/reports.types";

export type DailyReportViewStatus = "loading" | "error" | "empty" | "ready";

export interface DailyReportViewProps {
  status: DailyReportViewStatus;
  report?: DailyReportResponse;
  errorMessage?: string;
  selectedDate: string;
  onDateChange: (newDate: string) => void;
  onRetry: () => void;
}

export function DailyReportView({
  status,
  report,
  errorMessage,
  selectedDate,
  onDateChange,
  onRetry,
}: DailyReportViewProps) {
  const effectiveDate = selectedDate || report?.date || "";

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold text-text-light dark:text-text-dark">
          Reporte Diario de Ventas y Margen
        </h1>
        <p className="text-sm text-text-muted-light dark:text-text-muted-dark">
          Resumen diario de ventas, costos, margen bruto y medios de pago
        </p>
      </header>

      <DailyReportDateFilter
        selectedDate={effectiveDate}
        timezone={report?.timezone}
        onDateChange={onDateChange}
      />

      {status === "loading" ? (
        <div
          role="status"
          aria-live="polite"
          className="rounded-xl border border-border-light bg-surface-light p-6 text-center text-sm font-medium text-text-muted-light dark:border-border-dark dark:bg-surface-dark dark:text-text-muted-dark"
        >
          Cargando reporte diario...
        </div>
      ) : null}

      {status === "error" ? (
        <div
          role="alert"
          className="flex flex-col items-start justify-between gap-4 rounded-xl border border-error bg-error-light p-4 sm:flex-row sm:items-center"
        >
          <p className="text-sm font-medium text-error">
            {errorMessage ?? "No se pudo cargar el reporte diario"}
          </p>
          <button
            type="button"
            onClick={onRetry}
            className="touch-target rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-surface-light hover:bg-primary-hover"
          >
            Reintentar
          </button>
        </div>
      ) : null}

      {status === "empty" ? (
        <div
          role="status"
          className="rounded-xl border border-border-light bg-primary-light p-4 text-sm font-medium text-primary-dark dark:border-border-dark"
        >
          Sin ventas registradas en la fecha seleccionada
        </div>
      ) : null}

      {(status === "ready" || status === "empty") && report ? (
        <div className="space-y-6">
          <DailyReportKpiGrid report={report} />
          <PaymentBreakdownTable
            paymentBreakdown={report.payment_breakdown}
            totalSales={report.total_sales}
          />
        </div>
      ) : null}
    </main>
  );
}
