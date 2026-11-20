import type { DailyReportResponse } from "@/features/reports/types/reports.types";
import {
  formatCurrencyFromDecimal,
  formatPercentageFromDecimal,
  parseDecimalCents,
} from "@/features/reports/utils/formatters";

interface DailyReportKpiGridProps {
  report: DailyReportResponse;
}

export function DailyReportKpiGrid({ report }: DailyReportKpiGridProps) {
  const isNegativeMargin = parseDecimalCents(report.gross_margin) < 0n;

  return (
    <section
      aria-label="Indicadores clave del día"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
    >
      <article className="rounded-xl border border-border-light bg-surface-light p-4 dark:border-border-dark dark:bg-surface-dark">
        <h2 className="text-sm font-medium text-text-muted-light dark:text-text-muted-dark">
          Ventas Totales
        </h2>
        <p className="mt-2 text-2xl font-bold text-text-light dark:text-text-dark">
          {formatCurrencyFromDecimal(report.total_sales)}
        </p>
      </article>

      <article className="rounded-xl border border-border-light bg-surface-light p-4 dark:border-border-dark dark:bg-surface-dark">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-medium text-text-muted-light dark:text-text-muted-dark">
            Margen Bruto
          </h2>
          <span
            className={`rounded-md px-2 py-0.5 text-xs font-semibold ${
              isNegativeMargin ? "bg-error-light text-error" : "bg-primary-light text-primary-dark"
            }`}
          >
            {formatPercentageFromDecimal(report.margin_percentage)}
          </span>
        </div>
        <p
          className={`mt-2 text-2xl font-bold ${
            isNegativeMargin ? "text-error" : "text-text-light dark:text-text-dark"
          }`}
        >
          {formatCurrencyFromDecimal(report.gross_margin)}
        </p>
      </article>

      <article className="rounded-xl border border-border-light bg-surface-light p-4 dark:border-border-dark dark:bg-surface-dark">
        <h2 className="text-sm font-medium text-text-muted-light dark:text-text-muted-dark">
          Costo Mercadería
        </h2>
        <p className="mt-2 text-2xl font-bold text-text-light dark:text-text-dark">
          {formatCurrencyFromDecimal(report.total_cost)}
        </p>
      </article>

      <article className="rounded-xl border border-border-light bg-surface-light p-4 dark:border-border-dark dark:bg-surface-dark">
        <h2 className="text-sm font-medium text-text-muted-light dark:text-text-muted-dark">
          Tickets
        </h2>
        <p className="mt-2 text-2xl font-bold text-text-light dark:text-text-dark">
          {report.transactions_count}
        </p>
      </article>
    </section>
  );
}
