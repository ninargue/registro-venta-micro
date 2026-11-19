import { useEffect } from "react";
import type { SubmitEvent } from "react";
import { LoginForm } from "@/features/auth/components/LoginForm";
import { ThemeToggleButton } from "@/shared/ui/ThemeToggleButton";

export interface LoginPageProps {
  email?: string;
  password?: string;
  onEmailChange?: (value: string) => void;
  onPasswordChange?: (value: string) => void;
  onSubmit?: (event: SubmitEvent<HTMLFormElement>) => void;
  isLoading?: boolean;
  errorMessage?: string | null;
  fieldErrors?: {
    email?: boolean;
    password?: boolean;
  };
  isDark?: boolean;
  onToggleTheme?: () => void;
}

const NOOP = () => undefined;
const NOOP_SUBMIT = (event: SubmitEvent<HTMLFormElement>) => {
  event.preventDefault();
};

/**
 * Vista presentacional pura de /login con tarjeta accesible, título y selector de tema.
 */
export function LoginPage({
  email = "",
  password = "",
  onEmailChange = NOOP,
  onPasswordChange = NOOP,
  onSubmit = NOOP_SUBMIT,
  isLoading = false,
  errorMessage = null,
  fieldErrors,
  isDark = false,
  onToggleTheme = NOOP,
}: LoginPageProps) {
  useEffect(() => {
    document.title = "Iniciar Sesión — registro-venta-micro";
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--color-background-light)] p-4 dark:bg-[var(--color-background-dark)]">
      <section
        role="region"
        aria-label="Tarjeta de inicio de sesión"
        className="w-full max-w-md rounded-[var(--radius-control)] border border-[var(--color-border-light)] bg-[var(--color-surface-light)] p-6 shadow-sm dark:border-[var(--color-border-dark)] dark:bg-[var(--color-surface-dark)]"
      >
        <header className="mb-6 flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text-light)] dark:text-[var(--color-text-dark)]">
              registro-venta-micro
            </h1>
            <p className="text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted-dark)]">
              Ingresa las credenciales de tu negocio para comenzar a operar.
            </p>
          </div>

          <ThemeToggleButton isDark={isDark} onToggle={onToggleTheme} />
        </header>

        <LoginForm
          email={email}
          password={password}
          onEmailChange={onEmailChange}
          onPasswordChange={onPasswordChange}
          onSubmit={onSubmit}
          isLoading={isLoading}
          errorMessage={errorMessage}
          fieldErrors={fieldErrors}
        />
      </section>
    </main>
  );
}
