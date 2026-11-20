import type { ApiErrorResponse, DailyReportResponse } from "@/features/reports/types/reports.types";

export class ReportsApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ReportsApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return typeof record.code === "string" && typeof record.message === "string";
}

export async function fetchDailyReport(
  date?: string,
  signal?: AbortSignal,
): Promise<DailyReportResponse> {
  const trimmedDate = date?.trim();
  const endpoint =
    trimmedDate && trimmedDate.length > 0
      ? `/api/v1/reports/daily?date=${encodeURIComponent(trimmedDate)}`
      : "/api/v1/reports/daily";

  const response = await fetch(endpoint, {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    let errorCode = "HTTP_ERROR";
    let errorMessage = "No se pudo cargar el reporte diario";
    let errorDetails: unknown = null;

    try {
      const payload: unknown = await response.json();
      if (isApiErrorResponse(payload)) {
        errorCode = payload.code;
        errorMessage = payload.message;
        errorDetails = payload.details;
      }
    } catch {
      // Fallback when body is not valid JSON
    }

    throw new ReportsApiError(response.status, errorCode, errorMessage, errorDetails);
  }

  const data = (await response.json()) as DailyReportResponse;
  return data;
}
