import type { ErrorResponse, LoginResponse } from "@/features/auth/types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(status: number, errorResponse: ErrorResponse) {
    super(errorResponse.message);
    this.name = "ApiError";
    this.status = status;
    this.code = errorResponse.code;
    this.details = errorResponse.details ?? null;
  }
}

export class ApiNetworkError extends Error {
  constructor(message = "No se pudo conectar con el servidor.") {
    super(message);
    this.name = "ApiNetworkError";
  }
}

export interface ApiFetchOptions extends RequestInit {
  retryOnUnauthorized?: boolean;
}

let refreshInFlight: Promise<LoginResponse> | null = null;

async function parseErrorResponse(response: Response): Promise<ErrorResponse> {
  try {
    const data: unknown = await response.json();
    if (
      typeof data === "object" &&
      data !== null &&
      "code" in data &&
      "message" in data &&
      typeof (data as ErrorResponse).code === "string" &&
      typeof (data as ErrorResponse).message === "string"
    ) {
      return data as ErrorResponse;
    }
  } catch {
    // Cuerpo no JSON o vacío
  }

  return {
    code: `HTTP_${response.status}`,
    message: "Ocurrió un error inesperado al comunicarse con el servidor.",
    details: null,
  };
}

async function performFetch(url: string, init: RequestInit): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  try {
    return await fetch(url, {
      ...init,
      credentials: "include",
      headers,
    });
  } catch {
    throw new ApiNetworkError();
  }
}

/**
 * Ejecuta POST /api/v1/auth/refresh deduplicando llamadas concurrentes.
 */
export async function refreshSessionOnce(): Promise<LoginResponse> {
  if (refreshInFlight) {
    return refreshInFlight;
  }

  refreshInFlight = (async () => {
    const response = await performFetch("/api/v1/auth/refresh", {
      method: "POST",
    });

    if (!response.ok) {
      const errorBody = await parseErrorResponse(response);
      throw new ApiError(response.status, errorBody);
    }

    return (await response.json()) as LoginResponse;
  })();

  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

/**
 * Wrapper HTTP centralizado con credentials: "include", errores tipados ErrorResponse
 * y renovación única automática ante 401.
 */
export async function apiFetch<T>(url: string, options: ApiFetchOptions = {}): Promise<T> {
  const { retryOnUnauthorized = true, ...init } = options;

  let response = await performFetch(url, init);

  if (response.status === 401 && retryOnUnauthorized) {
    await refreshSessionOnce();
    response = await performFetch(url, init);
  }

  if (!response.ok) {
    const errorBody = await parseErrorResponse(response);
    throw new ApiError(response.status, errorBody);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
