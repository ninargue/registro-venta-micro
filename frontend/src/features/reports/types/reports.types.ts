export interface PaymentMethodBreakdown {
  cash: string;
  card: string;
  transfer: string;
}

export interface DailyReportResponse {
  date: string;
  timezone: string;
  total_sales: string;
  transactions_count: number;
  total_cost: string;
  gross_margin: string;
  margin_percentage: string;
  payment_breakdown: PaymentMethodBreakdown;
}

export interface ApiErrorResponse {
  code: string;
  message: string;
  details?: unknown;
}
