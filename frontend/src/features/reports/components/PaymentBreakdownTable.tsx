import type { PaymentMethodBreakdown } from "@/features/reports/types/reports.types";
import {
  calculatePaymentSharePercentage,
  formatCurrencyFromDecimal,
} from "@/features/reports/utils/formatters";

interface PaymentBreakdownTableProps {
  paymentBreakdown: PaymentMethodBreakdown;
  totalSales: string;
}

const PAYMENT_ROWS: ReadonlyArray<{
  key: keyof PaymentMethodBreakdown;
  label: string;
}> = [
  { key: "cash", label: "Efectivo" },
  { key: "card", label: "Tarjeta" },
  { key: "transfer", label: "Transferencia" },
];

export function PaymentBreakdownTable({
  paymentBreakdown,
  totalSales,
}: PaymentBreakdownTableProps) {
  return (
    <section
      aria-labelledby="payment-breakdown-heading"
      className="rounded-xl border border-border-light bg-surface-light p-4 dark:border-border-dark dark:bg-surface-dark"
    >
      <h2
        id="payment-breakdown-heading"
        className="text-base font-semibold text-text-light dark:text-text-dark"
      >
        Desglose por Medio de Pago
      </h2>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-border-light text-text-muted-light dark:border-border-dark dark:text-text-muted-dark">
              <th scope="col" className="py-2 pr-4 font-medium">
                Medio de pago
              </th>
              <th scope="col" className="py-2 pr-4 font-medium">
                Monto
              </th>
              <th scope="col" className="py-2 font-medium">
                Proporción
              </th>
            </tr>
          </thead>
          <tbody>
            {PAYMENT_ROWS.map(({ key, label }) => {
              const rawAmount = paymentBreakdown[key];
              const formattedAmount = formatCurrencyFromDecimal(rawAmount);
              const sharePercentage = calculatePaymentSharePercentage(rawAmount, totalSales);

              return (
                <tr
                  key={key}
                  className="border-b border-border-light last:border-b-0 dark:border-border-dark"
                >
                  <th
                    scope="row"
                    className="py-3 pr-4 font-medium text-text-light dark:text-text-dark"
                  >
                    {label}
                  </th>
                  <td className="py-3 pr-4 font-semibold text-text-light dark:text-text-dark">
                    {formattedAmount}
                  </td>
                  <td className="py-3 text-text-muted-light dark:text-text-muted-dark">
                    {sharePercentage}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
