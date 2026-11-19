import type { ButtonHTMLAttributes, ReactNode } from "react";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger";
  isLoading?: boolean;
  children: ReactNode;
}

const VARIANT_CLASSES: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary:
    "bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-hover)] active:bg-[var(--color-primary-dark)] border-transparent",
  secondary:
    "bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)] text-[var(--color-text-light)] dark:text-[var(--color-text-dark)] border-[var(--color-border-light)] dark:border-[var(--color-border-dark)] hover:bg-[var(--color-background-light)] dark:hover:bg-[var(--color-background-dark)]",
  danger: "bg-[var(--color-error)] text-white hover:opacity-90 border-transparent",
};

/**
 * Botón táctil accesible (>= 48px) con soporte de estado de carga anti-doble envío.
 */
export function Button({
  variant = "primary",
  isLoading = false,
  disabled = false,
  type = "button",
  className = "",
  children,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || isLoading;

  return (
    <button
      type={type}
      disabled={isDisabled}
      aria-busy={isLoading || undefined}
      className={[
        "touch-target inline-flex items-center justify-center gap-2 rounded-[var(--radius-control)] border px-4 py-3 text-base font-semibold transition-colors",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
        "disabled:cursor-not-allowed disabled:opacity-60",
        VARIANT_CLASSES[variant],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    >
      {isLoading ? (
        <span
          aria-hidden="true"
          className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      ) : null}
      <span>{children}</span>
    </button>
  );
}
