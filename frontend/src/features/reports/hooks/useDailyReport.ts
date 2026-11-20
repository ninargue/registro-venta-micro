import { useQuery } from "@tanstack/react-query";

import { fetchDailyReport, ReportsApiError } from "@/features/reports/api/reportsApi";
import type { DailyReportResponse } from "@/features/reports/types/reports.types";

export function useDailyReport(date?: string) {
  const normalizedDate = date && date.trim().length > 0 ? date.trim() : undefined;

  return useQuery<DailyReportResponse>({
    queryKey: ["reports", "daily", normalizedDate ?? "today"],
    queryFn: ({ signal }) => fetchDailyReport(normalizedDate, signal),
    retry: (failureCount, error) => {
      if (error instanceof ReportsApiError && error.status >= 400 && error.status < 500) {
        return false;
      }
      return failureCount < 1;
    },
  });
}
