import { describe, expect, it } from "vitest";

import {
  calculatePaymentSharePercentage,
  formatCurrencyFromDecimal,
  formatPercentageFromDecimal,
  parseDecimalCents,
} from "@/features/reports/utils/formatters";

describe("formatters — Formateo monetario y porcentual sin deriva de punto flotante", () => {
  describe("parseDecimalCents", () => {
    it("convierte cadenas decimales exactas a centavos enteros en BigInt", () => {
      expect(parseDecimalCents("30000.00")).toBe(3000000n);
      expect(parseDecimalCents("0.00")).toBe(0n);
      expect(parseDecimalCents("-250.00")).toBe(-25000n);
      expect(parseDecimalCents("19.99")).toBe(1999n);
    });
  });

  describe("formatCurrencyFromDecimal", () => {
    it("Scenario: Owner views daily report with sales and positive gross margin (state: ready) — formatea montos positivos a moneda local con 2 decimales", () => {
      expect(formatCurrencyFromDecimal("30000.00")).toBe("$30.000,00");
      expect(formatCurrencyFromDecimal("21000.00")).toBe("$21.000,00");
      expect(formatCurrencyFromDecimal("9000.00")).toBe("$9.000,00");
    });

    it("Scenario: Day without sales displays empty state notice and zero KPIs (state: empty) — formatea valores en cero como $0,00", () => {
      expect(formatCurrencyFromDecimal("0.00")).toBe("$0,00");
    });

    it("Scenario: Owner views daily report with negative gross margin (state: ready) — preserva el signo negativo en márgenes negativos", () => {
      expect(formatCurrencyFromDecimal("-250.00")).toBe("-$250,00");
    });
  });

  describe("formatPercentageFromDecimal", () => {
    it("formatea porcentajes positivos, cero y negativos a 2 decimales con sufijo %", () => {
      expect(formatPercentageFromDecimal("30.00")).toBe("30.00%");
      expect(formatPercentageFromDecimal("0.00")).toBe("0.00%");
      expect(formatPercentageFromDecimal("-25.00")).toBe("-25.00%");
    });
  });

  describe("calculatePaymentSharePercentage", () => {
    it("Scenario: Payment method breakdown renders amounts and proportions for all three methods — calcula proporciones exactas con redondeo HALF_UP a 2 decimales", () => {
      expect(calculatePaymentSharePercentage("15000.00", "30000.00")).toBe("50.00%");
      expect(calculatePaymentSharePercentage("10000.00", "30000.00")).toBe("33.33%");
      expect(calculatePaymentSharePercentage("5000.00", "30000.00")).toBe("16.67%");
    });

    it("Scenario: Day without sales displays empty state notice and zero KPIs (state: empty) — protege contra división por cero devolviendo 0.00% cuando total_sales es 0.00", () => {
      expect(calculatePaymentSharePercentage("0.00", "0.00")).toBe("0.00%");
    });

    it("Scenario: Day without sales displays empty state notice and zero KPIs (state: empty) — con total_sales 0.00 y monto de método positivo no lanza y devuelve 0.00%", () => {
      expect(() => calculatePaymentSharePercentage("100.00", "0.00")).not.toThrow();
      expect(calculatePaymentSharePercentage("100.00", "0.00")).toBe("0.00%");
    });

    it("Scenario: Day without sales displays empty state notice and zero KPIs (state: empty) — con total_sales negativo (payload inconsistente) devuelve 0.00% sin dividir", () => {
      expect(calculatePaymentSharePercentage("100.00", "-5.00")).toBe("0.00%");
    });
  });
});
