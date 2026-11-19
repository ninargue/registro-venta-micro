import type { InputHTMLAttributes, Ref } from "react";

export interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id"> {
  id: string;
  label: string;
  hasError?: boolean;
  helperText?: string;
  inputRef?: Ref<HTMLInputElement>;
}

/**
 * Campo de texto accesible con etiqueta asociada, área táctil >= 48px y soporte aria-invalid.
 */
export function TextField({
  id,
  label,
  hasError = false,
  helperText,
  required = false,
  inputRef,
  className = "",
  "aria-describedby": ariaDescribedBy,
  "aria-invalid": ariaInvalid,
  ...props
}: TextFieldProps) {
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

      <input
        id={id}
        ref={inputRef}
        required={required}
        aria-invalid={isInvalid}
        aria-describedby={describedBy}
        className={[
          "touch-target w-full rounded-[var(--radius-control)] border px-3 py-2.5 text-base transition-colors",
          "bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)]",
          "text-[var(--color-text-light)] dark:text-[var(--color-text-dark)]",
          "placeholder:text-[var(--color-text-muted-light)] dark:placeholder:text-[var(--color-text-muted-dark)]",
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
      />

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
