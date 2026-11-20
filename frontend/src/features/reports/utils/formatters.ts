const DECIMAL_PATTERN = /^(-)?(\d+)(?:\.(\d{1,2}))?$/;

function formatIntegerThousands(intPart: string): string {
  return intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

export function parseDecimalCents(decimalStr: string): bigint {
  const trimmed = decimalStr.trim();
  const match = DECIMAL_PATTERN.exec(trimmed);
  if (!match) {
    throw new Error(`Invalid decimal string: ${decimalStr}`);
  }
  const isNegative = trimmed.startsWith("-");
  const unsigned = isNegative ? trimmed.slice(1) : trimmed;
  const dotIndex = unsigned.indexOf(".");
  const intPart = dotIndex === -1 ? unsigned : unsigned.slice(0, dotIndex);
  const fracPart = (dotIndex === -1 ? "" : unsigned.slice(dotIndex + 1)).padEnd(2, "0");
  const absCents = BigInt(intPart) * 100n + BigInt(fracPart);
  return isNegative && absCents > 0n ? -absCents : absCents;
}

export function formatCurrencyFromDecimal(decimalStr: string): string {
  const cents = parseDecimalCents(decimalStr);
  const isNegative = cents < 0n;
  const absCents = isNegative ? -cents : cents;
  const intUnits = (absCents / 100n).toString();
  const fracUnits = (absCents % 100n).toString().padStart(2, "0");
  const formattedInt = formatIntegerThousands(intUnits);
  const prefix = isNegative ? "-$" : "$";
  return `${prefix}${formattedInt},${fracUnits}`;
}

export function formatPercentageFromDecimal(decimalStr: string): string {
  const cents = parseDecimalCents(decimalStr);
  const isNegative = cents < 0n;
  const absCents = isNegative ? -cents : cents;
  const intUnits = (absCents / 100n).toString();
  const fracUnits = (absCents % 100n).toString().padStart(2, "0");
  const sign = isNegative ? "-" : "";
  return `${sign}${intUnits}.${fracUnits}%`;
}

export function calculatePaymentSharePercentage(
  methodAmountStr: string,
  totalSalesStr: string,
): string {
  const totalSalesCents = parseDecimalCents(totalSalesStr);
  if (totalSalesCents <= 0n) {
    return "0.00%";
  }
  const methodCents = parseDecimalCents(methodAmountStr);
  if (methodCents <= 0n) {
    return "0.00%";
  }
  const scaledBasisPoints = (methodCents * 10000n + totalSalesCents / 2n) / totalSalesCents;
  const intUnits = (scaledBasisPoints / 100n).toString();
  const fracUnits = (scaledBasisPoints % 100n).toString().padStart(2, "0");
  return `${intUnits}.${fracUnits}%`;
}
