import type { Ref, SelectHTMLAttributes } from "react";
import { SUPPORTED_COUNTRIES } from "@/shared/constants/countries";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectFieldProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "id"> {
  id: string;
  label: string;
  options?: ReadonlyArray<SelectOption>;
  placeholderOption?: string;
  hasError?: boolean;
  helperText?: string;
  selectRef?: Ref<HTMLSelectElement>;
}

const DEFAULT_COUNTRY_OPTIONS: ReadonlyArray<SelectOption> = SUPPORTED_COUNTRIES.map((country) => ({
  value: country.code,
  label: `${country.name} (${country.code})`,
}));

/**
 * Selector nativo accesible (>= 48px) conectado por defecto al catálogo SUPPORTED_COUNTRIES.
 */
export function SelectField({
  id,
  label,
  options = DEFAULT_COUNTRY_OPTIONS,
  placeholderOption = "Selecciona una opción",
  hasError = false,
  helperText,
  required = false,
  selectRef,
  className = "",
  "aria-describedby": ariaDescribedBy,
  "aria-invalid": ariaInvalid,
  ...props
}: SelectFieldProps) {
  const helperId = helperText ? `${id}-helper` : undefined;
  const describedBy = [ariaDescribedBy, helperId].filter(Boolean).join(" ") || undefined;
  const isInvalid = ariaInvalid ?? (hasError ? true : undefined);

  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={id}
        className="text-sm font-medium text-[var(--color-text-light)] dark:text-[var(--color-text-dark)]"
      >
        {label}
        {required ? (
          <span aria-hidden="true" className="ml-0.5 text-[var(--color-error)]">
            *
          </span>
        ) : null}
      </label>

      <select
        id={id}
        ref={selectRef}
        required={required}
        aria-invalid={isInvalid}
        aria-describedby={describedBy}
        className={[
          "touch-target w-full rounded-[var(--radius-control)] border px-3 py-2.5 text-base transition-colors",
          "bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)]",
          "text-[var(--color-text-light)] dark:text-[var(--color-text-dark)]",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
          "disabled:cursor-not-allowed disabled:opacity-60",
          isInvalid
            ? "border-[var(--color-error)]"
            : "border-[var(--color-border-light)] dark:border-[var(--color-border-dark)]",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
        {...props}
      >
        <option value="">{placeholderOption}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      {helperText ? (
        <p
          id={helperId}
          className="text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted-dark)]"
        >
          {helperText}
        </p>
      ) : null}
    </div>
  );
}
