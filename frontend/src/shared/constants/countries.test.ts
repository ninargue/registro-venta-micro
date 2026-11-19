import { describe, expect, it } from "vitest";
import { COUNTRY_TIMEZONES, SUPPORTED_COUNTRIES } from "./countries";

describe("Catálogo de países y zonas horarias (countries.ts)", () => {
  it("contiene una lista no vacía de países con códigos ISO únicos", () => {
    expect(SUPPORTED_COUNTRIES.length).toBeGreaterThan(0);
    const codes = SUPPORTED_COUNTRIES.map((c) => c.code);
    const uniqueCodes = new Set(codes);
    expect(uniqueCodes.size).toBe(codes.length);
  });

  it("todas las zonas horarias son válidas según Intl.DateTimeFormat (IANA)", () => {
    for (const country of SUPPORTED_COUNTRIES) {
      expect(() => {
        Intl.DateTimeFormat(undefined, { timeZone: country.defaultTimezone });
      }).not.toThrow();
    }
  });

  it("COUNTRY_TIMEZONES mapea exactamente el código de cada país con su timezone", () => {
    for (const country of SUPPORTED_COUNTRIES) {
      expect(COUNTRY_TIMEZONES[country.code]).toBe(country.defaultTimezone);
    }
  });
});
