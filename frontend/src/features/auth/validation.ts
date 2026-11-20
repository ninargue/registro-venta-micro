import { COUNTRY_TIMEZONES } from "@/shared/constants/countries";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_EMAIL_LENGTH = 254;
const MAX_PASSWORD_LENGTH = 128;
const MAX_BUSINESS_NAME_LENGTH = 100;

export interface LoginValidationResult {
  valid: boolean;
  errorMessage: string | null;
  fieldErrors: {
    email?: boolean;
    password?: boolean;
  };
  normalizedEmail: string;
}

export interface OnboardingValidationResult {
  valid: boolean;
  errorMessage: string | null;
  fieldErrors: {
    name?: boolean;
    country?: boolean;
  };
  normalizedName: string;
}

/**
 * Valida credenciales de login en el cliente antes de enviar a POST /api/v1/auth/login.
 */
export function validateLoginInput(email: string, password: string): LoginValidationResult {
  const normalizedEmail = email.trim();
  const fieldErrors: { email?: boolean; password?: boolean } = {};
  const messages: string[] = [];

  if (normalizedEmail.length === 0) {
    fieldErrors.email = true;
    messages.push("Ingresa tu correo electrónico.");
  } else if (normalizedEmail.length > MAX_EMAIL_LENGTH || !EMAIL_PATTERN.test(normalizedEmail)) {
    fieldErrors.email = true;
    messages.push("Ingresa un correo electrónico válido.");
  }

  if (password.length === 0) {
    fieldErrors.password = true;
    messages.push("Ingresa tu contraseña.");
  } else if (password.length > MAX_PASSWORD_LENGTH) {
    fieldErrors.password = true;
    messages.push("La contraseña supera la longitud máxima permitida.");
  }

  return {
    valid: messages.length === 0,
    errorMessage: messages[0] ?? null,
    fieldErrors,
    normalizedEmail,
  };
}

/**
 * Valida nombre del negocio y país de operación antes de enviar a POST /api/v1/auth/onboarding.
 */
export function validateOnboardingInput(name: string, country: string): OnboardingValidationResult {
  const normalizedName = name.trim();
  const fieldErrors: { name?: boolean; country?: boolean } = {};
  const messages: string[] = [];

  if (normalizedName.length === 0) {
    fieldErrors.name = true;
    messages.push("Ingresa el nombre de tu negocio.");
  } else if (normalizedName.length > MAX_BUSINESS_NAME_LENGTH) {
    fieldErrors.name = true;
    messages.push("El nombre del negocio no puede superar los 100 caracteres.");
  }

  if (!country || !(country in COUNTRY_TIMEZONES)) {
    fieldErrors.country = true;
    messages.push("Selecciona un país de operación.");
  }

  return {
    valid: messages.length === 0,
    errorMessage: messages[0] ?? null,
    fieldErrors,
    normalizedName,
  };
}
