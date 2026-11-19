/**
 * Catálogo de países soportados en el onboarding del negocio y resolución de zonas horarias IANA.
 * Debe coincidir estrictamente con COUNTRY_TIMEZONES en backend/app/modules/auth/schemas.py.
 */

export const SUPPORTED_COUNTRIES = [
  { code: "AR", name: "Argentina", defaultTimezone: "America/Argentina/Buenos_Aires" },
  { code: "BO", name: "Bolivia", defaultTimezone: "America/La_Paz" },
  { code: "BR", name: "Brasil", defaultTimezone: "America/Sao_Paulo" },
  { code: "CL", name: "Chile", defaultTimezone: "America/Santiago" },
  { code: "CO", name: "Colombia", defaultTimezone: "America/Bogota" },
  { code: "EC", name: "Ecuador", defaultTimezone: "America/Guayaquil" },
  { code: "ES", name: "España", defaultTimezone: "Europe/Madrid" },
  { code: "MX", name: "México", defaultTimezone: "America/Mexico_City" },
  { code: "PE", name: "Perú", defaultTimezone: "America/Lima" },
  { code: "PY", name: "Paraguay", defaultTimezone: "America/Asuncion" },
  { code: "US", name: "Estados Unidos", defaultTimezone: "America/New_York" },
  { code: "UY", name: "Uruguay", defaultTimezone: "America/Montevideo" },
] as const;

export type CountryOption = (typeof SUPPORTED_COUNTRIES)[number];
export type SupportedCountryCode = CountryOption["code"];
export type SupportedTimezone = CountryOption["defaultTimezone"];

export const COUNTRY_TIMEZONES: Record<SupportedCountryCode, SupportedTimezone> =
  Object.fromEntries(
    SUPPORTED_COUNTRIES.map((c) => [c.code, c.defaultTimezone]),
  ) as Record<SupportedCountryCode, SupportedTimezone>;
