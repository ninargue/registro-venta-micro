import { lazy, Suspense, useState, type SubmitEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { useAuthSession } from "@/features/auth/AuthContext";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { useTheme } from "@/features/auth/ThemeContext";
import { validateLoginInput } from "@/features/auth/validation";
import { ApiError, ApiNetworkError } from "@/lib/api-client";

const LazyOnboardingContainer = lazy(() =>
  import("@/features/auth/containers/OnboardingContainer").then((module) => ({
    default: module.OnboardingContainer,
  })),
);

function mapLoginErrorMessage(error: unknown): string {
  if (error instanceof ApiNetworkError) {
    return "No se pudo conectar con el servidor. Verifica tu conexión e intenta nuevamente.";
  }

  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        return "Correo electrónico o contraseña incorrectos.";
      case 422:
        return error.message || "Los datos ingresados no son válidos.";
      case 429:
        return "Demasiados intentos fallidos. Espera un momento antes de volver a intentar.";
      case 502:
        return "El servicio de autenticación no está disponible temporalmente.";
      case 503:
        return "El servicio tardó demasiado en responder. Intenta nuevamente.";
      default:
        return error.message || "No se pudo iniciar sesión. Intenta nuevamente.";
    }
  }

  return "Ocurrió un error inesperado al iniciar sesión.";
}

export function LoginContainer() {
  const navigate = useNavigate();
  const { status, sessionAlert, clearSessionAlert, login } = useAuthSession();
  const { isDark, toggleTheme } = useTheme();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{ email?: boolean; password?: boolean }>({});
  const [isLoading, setIsLoading] = useState(false);

  if (status === "authenticated") {
    return <Navigate to="/" replace />;
  }

  const handleEmailChange = (value: string) => {
    setEmail(value);
    if (fieldErrors.email) {
      setFieldErrors((prev) => ({ ...prev, email: false }));
    }
    if (errorMessage) {
      setErrorMessage(null);
    }
  };

  const handlePasswordChange = (value: string) => {
    setPassword(value);
    if (fieldErrors.password) {
      setFieldErrors((prev) => ({ ...prev, password: false }));
    }
    if (errorMessage) {
      setErrorMessage(null);
    }
  };

  const submitLogin = async () => {
    if (isLoading) {
      return;
    }

    clearSessionAlert();
    const validation = validateLoginInput(email, password);
    if (!validation.valid) {
      setFieldErrors(validation.fieldErrors);
      setErrorMessage(validation.errorMessage);
      return;
    }

    setFieldErrors({});
    setErrorMessage(null);
    setIsLoading(true);

    try {
      const ctx = await login({
        email: validation.normalizedEmail,
        password,
      });

      if (!ctx.requires_onboarding) {
        void navigate("/", { replace: true });
      }
    } catch (error) {
      setErrorMessage(mapLoginErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    void submitLogin();
  };

  return (
    <>
      <LoginPage
        email={email}
        password={password}
        onEmailChange={handleEmailChange}
        onPasswordChange={handlePasswordChange}
        onSubmit={handleSubmit}
        isLoading={isLoading}
        errorMessage={errorMessage ?? sessionAlert}
        fieldErrors={fieldErrors}
        isDark={isDark}
        onToggleTheme={toggleTheme}
      />
      {status === "onboarding_required" ? (
        <Suspense fallback={null}>
          <LazyOnboardingContainer allowLogout />
        </Suspense>
      ) : null}
    </>
  );
}
