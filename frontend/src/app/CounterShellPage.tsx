import { Button } from "@/shared/ui/Button";
import { ThemeToggleButton } from "@/shared/ui/ThemeToggleButton";

export interface CounterShellPageProps {
  businessName?: string | null;
  userEmail?: string | null;
  country?: string | null;
  timezone?: string | null;
  isLoading?: boolean;
  isLoggingOut?: boolean;
  onLogout?: () => void;
  isDark?: boolean;
  onToggleTheme?: () => void;
}

const NOOP = () => undefined;

/**
 * Vista presentacional pura del shell principal (/) con contexto del comercio y cierre de sesión.
 */
export function CounterShellPage({
  businessName = null,
  userEmail = null,
  country = null,
  timezone = null,
  isLoading = false,
  isLoggingOut = false,
  onLogout = NOOP,
  isDark = false,
  onToggleTheme = NOOP,
}: CounterShellPageProps) {
  return (
    <main
      aria-busy={isLoading || undefined}
      className="min-h-screen bg-[var(--color-background-light)] p-4 text-[var(--color-text-light)] dark:bg-[var(--color-background-dark)] dark:text-[var(--color-text-dark)]"
    >
      <div className="mx-auto flex max-w-4xl flex-col gap-6">
        <header className="flex flex-wrap items-center justify-between gap-4 rounded-[var(--radius-control)] border border-[var(--color-border-light)] bg-[var(--color-surface-light)] p-4 shadow-xs dark:border-[var(--color-border-dark)] dark:bg-[var(--color-surface-dark)]">
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-bold tracking-tight">registro-venta-micro</h1>
            {businessName ? (
              <p className="text-base font-medium text-[var(--color-primary)]">{businessName}</p>
            ) : null}
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggleButton isDark={isDark} onToggle={onToggleTheme} />
            {!isLoading ? (
              <Button type="button" variant="secondary" onClick={onLogout} isLoading={isLoggingOut}>
                Cerrar sesión
              </Button>
            ) : null}
          </div>
        </header>

        {isLoading ? (
          <p
            role="status"
            className="text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted-dark)]"
          >
            Verificando sesión...
          </p>
        ) : (
          <section
            aria-label="Resumen de sesión"
            className="rounded-[var(--radius-control)] border border-[var(--color-border-light)] bg-[var(--color-surface-light)] p-4 dark:border-[var(--color-border-dark)] dark:bg-[var(--color-surface-dark)]"
          >
            <dl className="grid gap-3 text-sm sm:grid-cols-3">
              {userEmail ? (
                <div>
                  <dt className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted-dark)]">
                    Usuario
                  </dt>
                  <dd className="font-medium">{userEmail}</dd>
                </div>
              ) : null}
              {country ? (
                <div>
                  <dt className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted-dark)]">
                    País
                  </dt>
                  <dd className="font-medium">{country}</dd>
                </div>
              ) : null}
              {timezone ? (
                <div>
                  <dt className="text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted-dark)]">
                    Zona horaria
                  </dt>
                  <dd className="font-medium">{timezone}</dd>
                </div>
              ) : null}
            </dl>
          </section>
        )}
      </div>
    </main>
  );
}
