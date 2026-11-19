export interface ErrorAlertProps {
  id?: string;
  message?: string | null;
  className?: string;
}

/**
 * Alerta accesible (role="alert") para errores de validación o respuesta de API.
 */
export function ErrorAlert({ id, message, className = "" }: ErrorAlertProps) {
  if (!message) {
    return null;
  }

  return (
    <div
      id={id}
      role="alert"
      aria-live="assertive"
      className={[
        "rounded-[var(--radius-control)] border px-3.5 py-3 text-sm font-medium",
        "border-[var(--color-error-border-light)] bg-[var(--color-error-light)] text-[var(--color-error)]",
        "dark:border-[var(--color-error-border-dark)] dark:bg-[var(--color-error-dark)] dark:text-[var(--color-text-dark)]",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {message}
    </div>
  );
}
