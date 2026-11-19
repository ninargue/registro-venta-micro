import { useState, type SubmitEvent } from "react";
import { useNavigate } from "react-router";
import { useAuthSession } from "@/features/auth/AuthContext";
import { OnboardingModal } from "@/features/auth/components/OnboardingModal";
import { validateOnboardingInput } from "@/features/auth/validation";
import { ApiError, ApiNetworkError } from "@/lib/api-client";

function mapOnboardingErrorMessage(error: unknown): string {
  if (error instanceof ApiNetworkError) {
    return "No se pudo conectar con el servidor. Verifica tu conexión e intenta nuevamente.";
  }

  if (error instanceof ApiError) {
    if (error.status === 409) {
      return error.message || "Ya existe un comercio registrado para esta cuenta.";
    }
    if (error.status === 422) {
      return error.message || "Verifica el nombre del negocio y el país seleccionado.";
    }
    return error.message || "No se pudo registrar tu comercio. Intenta nuevamente.";
  }

  return "Ocurrió un error inesperado al registrar tu comercio.";
}

export interface OnboardingContainerProps {
  allowLogout?: boolean;
}

export function OnboardingContainer({ allowLogout = true }: OnboardingContainerProps) {
  const navigate = useNavigate();
  const { completeOnboarding, logout } = useAuthSession();

  const [businessName, setBusinessName] = useState("");
  const [country, setCountry] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{ name?: boolean; country?: boolean }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleBusinessNameChange = (value: string) => {
    setBusinessName(value);
    if (fieldErrors.name) {
      setFieldErrors((prev) => ({ ...prev, name: false }));
    }
    if (errorMessage) {
      setErrorMessage(null);
    }
  };

  const handleCountryChange = (value: string) => {
    setCountry(value);
    if (fieldErrors.country) {
      setFieldErrors((prev) => ({ ...prev, country: false }));
    }
    if (errorMessage) {
      setErrorMessage(null);
    }
  };

  const submitOnboarding = async () => {
    if (isLoading || isLoggingOut) {
      return;
    }

    const validation = validateOnboardingInput(businessName, country);
    if (!validation.valid) {
      setFieldErrors(validation.fieldErrors);
      setErrorMessage(validation.errorMessage);
      return;
    }

    setFieldErrors({});
    setErrorMessage(null);
    setIsLoading(true);

    try {
      await completeOnboarding({
        name: validation.normalizedName,
        country,
      });
      void navigate("/", { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        void navigate("/login", { replace: true });
        return;
      }
      setErrorMessage(mapOnboardingErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    void submitOnboarding();
  };

  const performLogout = async () => {
    if (isLoggingOut || isLoading) {
      return;
    }
    setIsLoggingOut(true);
    try {
      await logout();
      void navigate("/login", { replace: true });
    } finally {
      setIsLoggingOut(false);
    }
  };

  const handleLogout = () => {
    void performLogout();
  };

  return (
    <OnboardingModal
      isOpen
      businessName={businessName}
      country={country}
      onBusinessNameChange={handleBusinessNameChange}
      onCountryChange={handleCountryChange}
      onSubmit={handleSubmit}
      isLoading={isLoading}
      errorMessage={errorMessage}
      fieldErrors={fieldErrors}
      onLogout={allowLogout ? handleLogout : undefined}
      isLoggingOut={isLoggingOut}
    />
  );
}
