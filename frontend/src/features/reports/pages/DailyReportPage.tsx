import { useSearchParams } from "react-router";

import {
  DailyReportView,
  type DailyReportViewStatus,
} from "@/features/reports/components/DailyReportView";
import { useDailyReport } from "@/features/reports/hooks/useDailyReport";

export function DailyReportPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get("date")?.trim() ?? "";

  const { data, error, isPending, isError, refetch } = useDailyReport(
    dateParam.length > 0 ? dateParam : undefined,
  );

  let status: DailyReportViewStatus = "ready";
  if (isPending) {
    status = "loading";
  } else if (isError) {
    status = "error";
  } else if (data.transactions_count === 0) {
    status = "empty";
  }

  const selectedDate = dateParam || data?.date || "";

  const handleDateChange = (newDate: string) => {
    const trimmed = newDate.trim();
    if (trimmed.length > 0) {
      setSearchParams({ date: trimmed });
    } else {
      setSearchParams({});
    }
  };

  const handleRetry = () => {
    void refetch();
  };

  return (
    <DailyReportView
      status={status}
      report={data}
      errorMessage={error instanceof Error ? error.message : undefined}
      selectedDate={selectedDate}
      onDateChange={handleDateChange}
      onRetry={handleRetry}
    />
  );
}
