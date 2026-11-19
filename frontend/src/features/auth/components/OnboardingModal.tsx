import { useEffect, useRef } from "react";
import type { KeyboardEvent, SubmitEvent } from "react";
import { COUNTRY_TIMEZONES, type SupportedCountryCode } from "@/shared/constants/countries";
import { Button } from "@/shared/ui/Button";
import { ErrorAlert } from "@/shared/ui/ErrorAlert";
import { SelectField } from "@/shared/ui/SelectField";
import { TextField } from "@/shared/ui/TextField";

export interface OnboardingModalProps {
  isOpen: boolean;
  businessName: string;
  country: string;
  onBusinessNameChange: (value: string) => void;
  onCountryChange: (value: string) => void;
  onSubmit: (event: SubmitEvent<HTMLFormElement>) => void;
  isLoading?: boolean;
  errorMessage?: string | null;
  fieldErrors?: {
    name?: boolean;
    country?: boolean;
  };
  onLogout?: () => void;
  isLoggingOut?: boolean;
}

function isSupportedCountryCode(value: string): value is SupportedCountryCode {
  return value in COUNTRY_TIMEZONES;
}

/**
 * Modal accesible bloqueante de primer acceso para registrar el comercio único del dueño.
 * Impide cierre mediante Escape o clic en el fondo hasta completar el onboarding o cerrar sesión.
 */
export function OnboardingModal({
  isOpen,
  businessName,
  country,
  onBusinessNameChange,
  onCountryChange,
  onSubmit,
  isLoading = false,
  errorMessage = null,
  fieldErrors,
  onLogout,
  isLoggingOut = false,
}: OnboardingModalProps) {
  const internalNameRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      internalNameRef.current?.focus();
    }
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
    }
  };

  const selectedTimezone = isSupportedCountryCode(country) ? COUNTRY_TIMEZONES[country] : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto overscroll-contain bg-[var(--color-background-dark)]/70 p-4 backdrop-blur-xs"
      onKeyDown={handleKeyDown}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-heading"
        aria-describedby="onboarding-description"
        className="w-full max-w-md rounded-[var(--radius-control)] border border-[var(--color-border-light)] bg-[var(--color-surface-light)] p-6 shadow-xl dark:border-[var(--color-border-dark)] dark:bg-[var(--color-surface-dark)]"
      >
        <div className="mb-5 flex flex-col gap-2">
          <h2
            id="onboarding-heading"
            className="text-xl font-bold text-[var(--color-text-light)] dark:text-[var(--color-text-dark)]"
          >
            ¡Bienvenido! Configura tu comercio
          </h2>
          <p
            id="onboarding-description"
            className="text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted-dark)]"
          >
            Para comenzar a registrar ventas, indica el nombre de tu negocio y tu país de operación.
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          noValidate
          aria-busy={isLoading || undefined}
          className="flex flex-col gap-4"
        >
          <TextField
            id="onboarding-business-name"
            name="name"
            type="text"
            label="Nombre del negocio"
            placeholder="Ej. Kiosco Central"
            maxLength={100}
            value={businessName}
            onChange={(event) => {
              onBusinessNameChange(event.target.value);
            }}
            required
            enterKeyHint="next"
            hasError={Boolean(fieldErrors?.name)}
            disabled={isLoading || isLoggingOut}
            inputRef={internalNameRef}
          />

          <SelectField
            id="onboarding-country"
            name="country"
            label="País de operación"
            placeholderOption="Selecciona un país"
            helperText="Determina la moneda y la zona horaria de tus cierres de caja."
            value={country}
            onChange={(event) => {
              onCountryChange(event.target.value);
            }}
            required
            hasError={Boolean(fieldErrors?.country)}
            disabled={isLoading || isLoggingOut}
          />

          {selectedTimezone ? (
            <p className="text-xs text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted-dark)]">
              Zona horaria asignada: <span className="font-medium">{selectedTimezone}</span>
            </p>
          ) : null}

          <ErrorAlert id="onboarding-error-alert" message={errorMessage} />

          <div className="mt-2 flex flex-col gap-2">
            <Button type="submit" isLoading={isLoading} disabled={isLoggingOut} className="w-full">
              Crear Comercio y Entrar
            </Button>

            {onLogout ? (
              <Button
                type="button"
                variant="secondary"
                onClick={onLogout}
                isLoading={isLoggingOut}
                disabled={isLoading}
                className="w-full"
              >
                Cerrar sesión
              </Button>
            ) : null}
          </div>
        </form>
      </div>
    </div>
  );
}
