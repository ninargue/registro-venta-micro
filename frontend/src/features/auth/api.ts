import type {
  BusinessResponse,
  LoginRequest,
  LoginResponse,
  OnboardingRequest,
} from "@/features/auth/types";
import { apiFetch, ApiError, refreshSessionOnce } from "@/lib/api-client";

export function loginRequest(payload: LoginRequest): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
    retryOnUnauthorized: false,
  });
}

export function onboardingRequest(payload: OnboardingRequest): Promise<BusinessResponse> {
  return apiFetch<BusinessResponse>("/api/v1/auth/onboarding", {
    method: "POST",
    body: JSON.stringify(payload),
    retryOnUnauthorized: true,
  });
}

export function fetchMeRequest(): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/api/v1/auth/me", {
    method: "GET",
    retryOnUnauthorized: false,
  });
}

/**
 * Rehidrata la sesión vía /me; si responde 401, ejecuta /refresh una vez y usa su LoginResponse.
 */
export async function fetchMeWithRefresh(): Promise<LoginResponse> {
  try {
    return await fetchMeRequest();
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return refreshSessionOnce();
    }
    throw error;
  }
}

export function refreshSessionRequest(): Promise<LoginResponse> {
  return refreshSessionOnce();
}

export async function logoutRequest(): Promise<void> {
  await apiFetch<undefined>("/api/v1/auth/logout", {
    method: "POST",
    retryOnUnauthorized: false,
  });
}
