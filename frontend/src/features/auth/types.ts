/**
 * Tipos DTO trazados 1:1 con docs/api/openapi.json y estado público de sesión.
 */

export type BusinessRole = "owner" | "cashier";

export interface UserPayload {
  id: string;
  email: string;
}

export interface BusinessSummary {
  id: string;
  name: string;
  country: string;
  timezone: string;
  role: BusinessRole;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: UserPayload;
  requires_onboarding: boolean;
  business?: BusinessSummary | null;
}

export interface OnboardingRequest {
  name: string;
  country: string;
  timezone?: string | null;
}

export interface BusinessResponse {
  id: string;
  name: string;
  country: string;
  timezone: string;
  role: BusinessRole;
  created_at: string;
}

export interface ErrorResponse {
  code: string;
  message: string;
  details?: unknown;
}

export interface PublicAuthContext {
  user: UserPayload;
  requires_onboarding: boolean;
  business: BusinessSummary | null;
}

export type AuthStatus =
  "bootstrapping" | "unauthenticated" | "onboarding_required" | "authenticated";
