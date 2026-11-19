import type { BusinessSummary, PublicAuthContext } from "@/features/auth/types";

export const AUTH_CONTEXT_STORAGE_KEY = "rvm.auth.context";
export const THEME_STORAGE_KEY = "rvm.ui.theme";

export type ThemeMode = "light" | "dark";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isValidBusinessSummary(value: unknown): value is BusinessSummary {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.id === "string" &&
    typeof value.name === "string" &&
    typeof value.country === "string" &&
    typeof value.timezone === "string" &&
    (value.role === "owner" || value.role === "cashier")
  );
}

/**
 * Lee metadatos públicos de contexto desde localStorage. Nunca almacena ni retorna tokens JWT.
 */
export function readPublicAuthContext(): PublicAuthContext | null {
  try {
    const raw = localStorage.getItem(AUTH_CONTEXT_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed) || !isRecord(parsed.user)) {
      return null;
    }
    if (
      typeof parsed.user.id !== "string" ||
      typeof parsed.user.email !== "string" ||
      typeof parsed.requires_onboarding !== "boolean"
    ) {
      return null;
    }
    const business =
      parsed.business === null || parsed.business === undefined
        ? null
        : isValidBusinessSummary(parsed.business)
          ? parsed.business
          : null;

    return {
      user: {
        id: parsed.user.id,
        email: parsed.user.email,
      },
      requires_onboarding: parsed.requires_onboarding,
      business,
    };
  } catch {
    return null;
  }
}

/**
 * Persiste únicamente metadatos públicos permitidos (sin tokens ni contraseñas).
 */
export function writePublicAuthContext(context: PublicAuthContext): void {
  const sanitized: PublicAuthContext = {
    user: {
      id: context.user.id,
      email: context.user.email,
    },
    requires_onboarding: context.requires_onboarding,
    business: context.business
      ? {
          id: context.business.id,
          name: context.business.name,
          country: context.business.country,
          timezone: context.business.timezone,
          role: context.business.role,
        }
      : null,
  };

  try {
    localStorage.setItem(AUTH_CONTEXT_STORAGE_KEY, JSON.stringify(sanitized));
  } catch {
    // Ignorar errores de cuota o almacenamiento restringido
  }
}

export function clearPublicAuthContext(): void {
  try {
    localStorage.removeItem(AUTH_CONTEXT_STORAGE_KEY);
  } catch {
    // Ignorar errores de almacenamiento restringido
  }
}

export function readStoredTheme(): ThemeMode {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "dark" || stored === "light") {
      return stored;
    }
  } catch {
    // Ignorar errores de acceso a localStorage
  }

  if (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  ) {
    return "dark";
  }

  return "light";
}

export function writeStoredTheme(theme: ThemeMode): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Ignorar errores de acceso a localStorage
  }
}

export function applyThemeToDocument(theme: ThemeMode): void {
  if (typeof document === "undefined") {
    return;
  }
  const root = document.documentElement;
  root.setAttribute("data-theme", theme);
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}
