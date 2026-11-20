import type { Ref, SubmitEvent } from "react";
import { Button } from "@/shared/ui/Button";
import { ErrorAlert } from "@/shared/ui/ErrorAlert";
import { TextField } from "@/shared/ui/TextField";

export interface LoginFormProps {
  email: string;
  password: string;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: (event: SubmitEvent<HTMLFormElement>) => void;
  isLoading?: boolean;
  errorMessage?: string | null;
  fieldErrors?: {
    email?: boolean;
    password?: boolean;
  };
  emailInputRef?: Ref<HTMLInputElement>;
  passwordInputRef?: Ref<HTMLInputElement>;
}

/**
 * Formulario presentacional puro de inicio de sesión.
 */
export function LoginForm({
  email,
  password,
  onEmailChange,
  onPasswordChange,
  onSubmit,
  isLoading = false,
  errorMessage = null,
  fieldErrors,
  emailInputRef,
  passwordInputRef,
}: LoginFormProps) {
  return (
    <form
      onSubmit={onSubmit}
      noValidate
      aria-busy={isLoading || undefined}
      className="flex flex-col gap-4"
    >
      <TextField
        id="login-email"
        name="email"
        type="email"
        label="Correo electrónico"
        placeholder="dueño@negocio.com"
        value={email}
        onChange={(event) => {
          onEmailChange(event.target.value);
        }}
        required
        autoComplete="email"
        autoCapitalize="none"
        autoCorrect="off"
        spellCheck={false}
        enterKeyHint="next"
        hasError={Boolean(fieldErrors?.email)}
        disabled={isLoading}
        inputRef={emailInputRef}
      />

      <TextField
        id="login-password"
        name="password"
        type="password"
        label="Contraseña"
        value={password}
        onChange={(event) => {
          onPasswordChange(event.target.value);
        }}
        required
        autoComplete="current-password"
        enterKeyHint="done"
        hasError={Boolean(fieldErrors?.password)}
        disabled={isLoading}
        inputRef={passwordInputRef}
      />

      <ErrorAlert id="login-error-alert" message={errorMessage} />

      <Button type="submit" isLoading={isLoading} className="mt-2 w-full">
        Iniciar Sesión
      </Button>
    </form>
  );
}
