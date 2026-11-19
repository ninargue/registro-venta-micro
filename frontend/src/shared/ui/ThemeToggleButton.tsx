export interface ThemeToggleButtonProps {
  isDark: boolean;
  onToggle: () => void;
  className?: string;
}

/**
 * Botón accesible para alternar tema claro/oscuro con aria-pressed y objetivo táctil >= 48px.
 */
export function ThemeToggleButton({ isDark, onToggle, className = "" }: ThemeToggleButtonProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={isDark}
      aria-label="Alternar modo claro / modo oscuro"
      className={[
        "touch-target inline-flex items-center justify-center rounded-[var(--radius-control)] border p-2.5 transition-colors",
        "border-[var(--color-border-light)] bg-[var(--color-surface-light)] text-[var(--color-text-light)]",
        "hover:bg-[var(--color-background-light)]",
        "dark:border-[var(--color-border-dark)] dark:bg-[var(--color-surface-dark)] dark:text-[var(--color-text-dark)]",
        "dark:hover:bg-[var(--color-background-dark)]",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {isDark ? (
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-5 w-5"
        >
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2" />
          <path d="M12 20v2" />
          <path d="m4.93 4.93 1.41 1.41" />
          <path d="m17.66 17.66 1.41 1.41" />
          <path d="M2 12h2" />
          <path d="M20 12h2" />
          <path d="m6.34 17.66-1.41 1.41" />
          <path d="m19.07 4.93-1.41 1.41" />
        </svg>
      ) : (
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-5 w-5"
        >
          <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
        </svg>
      )}
    </button>
  );
}
