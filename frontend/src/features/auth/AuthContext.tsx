import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  fetchMeWithRefresh,
  loginRequest,
  logoutRequest,
  onboardingRequest,
} from "@/features/auth/api";
import {
  clearPublicAuthContext,
  readPublicAuthContext,
  writePublicAuthContext,
} from "@/features/auth/storage";
import type {
  AuthStatus,
  LoginRequest,
  LoginResponse,
  OnboardingRequest,
  PublicAuthContext,
} from "@/features/auth/types";
import { ApiError, ApiNetworkError, setOnSessionRefreshed } from "@/lib/api-client";

export const AUTH_SESSION_QUERY_KEY = ["auth", "session"] as const;

export interface AuthSessionContextValue {
  status: AuthStatus;
  context: PublicAuthContext | null;
  sessionAlert: string | null;
  clearSessionAlert: () => void;
  login: (payload: LoginRequest) => Promise<PublicAuthContext>;
  completeOnboarding: (payload: OnboardingRequest) => Promise<PublicAuthContext>;
  logout: () => Promise<void>;
  rehydrateSession: () => Promise<PublicAuthContext | null>;
}

const AuthSessionContext = createContext<AuthSessionContextValue | null>(null);

function toPublicAuthContext(response: LoginResponse): PublicAuthContext {
  return {
    user: {
      id: response.user.id,
      email: response.user.email,
    },
    requires_onboarding: response.requires_onboarding,
    business: response.business ?? null,
  };
}

async function resolveSessionFromServer(
  onTransientError?: (message: string) => void,
): Promise<PublicAuthContext | null> {
  try {
    const response = await fetchMeWithRefresh();
    const ctx = toPublicAuthContext(response);
    writePublicAuthContext(ctx);
    return ctx;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      clearPublicAuthContext();
      return null;
    }
    const isTransient =
      error instanceof ApiNetworkError ||
      (error instanceof ApiError && (error.status >= 500 || error.status === 429));
    if (isTransient) {
      const cached = readPublicAuthContext();
      if (cached && !cached.requires_onboarding) {
        return cached;
      }
      if (error instanceof ApiError) {
        onTransientError?.(
          "El servicio de autenticación no está disponible temporalmente. Intenta nuevamente.",
        );
      }
    }
    return null;
  }
}

export function AuthSessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [sessionAlert, setSessionAlert] = useState<string | null>(null);

  useEffect(() => {
    setOnSessionRefreshed((response) => {
      const ctx = toPublicAuthContext(response);
      writePublicAuthContext(ctx);
      queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, ctx);
    });
    return () => {
      setOnSessionRefreshed(null);
    };
  }, [queryClient]);

  const sessionQuery = useQuery<PublicAuthContext | null>({
    queryKey: AUTH_SESSION_QUERY_KEY,
    queryFn: () => resolveSessionFromServer(setSessionAlert),
    retry: false,
    refetchOnWindowFocus: false,
  });

  const clearSessionAlert = useCallback(() => {
    setSessionAlert(null);
  }, []);

  const login = useCallback(
    async (payload: LoginRequest): Promise<PublicAuthContext> => {
      const response = await loginRequest(payload);
      const ctx = toPublicAuthContext(response);
      writePublicAuthContext(ctx);
      queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, ctx);
      setSessionAlert(null);
      return ctx;
    },
    [queryClient],
  );

  const completeOnboarding = useCallback(
    async (payload: OnboardingRequest): Promise<PublicAuthContext> => {
      try {
        const business = await onboardingRequest(payload);
        const current =
          queryClient.getQueryData<PublicAuthContext | null>(AUTH_SESSION_QUERY_KEY) ??
          readPublicAuthContext();

        if (!current) {
          throw new Error("No existe una sesión autenticada activa.");
        }

        const nextContext: PublicAuthContext = {
          user: current.user,
          requires_onboarding: false,
          business: {
            id: business.id,
            name: business.name,
            country: business.country,
            timezone: business.timezone,
            role: business.role,
          },
        };

        writePublicAuthContext(nextContext);
        queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, nextContext);
        setSessionAlert(null);
        return nextContext;
      } catch (error) {
        if (error instanceof ApiError && error.status === 409) {
          try {
            const meResponse = await fetchMeWithRefresh();
            const reconciled = toPublicAuthContext(meResponse);
            if (!reconciled.requires_onboarding && reconciled.business) {
              writePublicAuthContext(reconciled);
              queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, reconciled);
              setSessionAlert(null);
              return reconciled;
            }
          } catch {
            // Si falla la reconciliación, propagamos el error 409 original
          }
        }

        if (error instanceof ApiError && error.status === 401) {
          clearPublicAuthContext();
          queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, null);
          setSessionAlert("Tu sesión expiró. Por favor, inicia sesión nuevamente.");
        }

        throw error;
      }
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch {
      // Si falla la red o el backend, completamos igualmente la limpieza local de sesión
    } finally {
      clearPublicAuthContext();
      queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, null);
      setSessionAlert(null);
    }
  }, [queryClient]);

  const rehydrateSession = useCallback(async (): Promise<PublicAuthContext | null> => {
    const ctx = await resolveSessionFromServer(setSessionAlert);
    queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, ctx);
    return ctx;
  }, [queryClient]);

  const context = sessionQuery.data ?? null;
  const status: AuthStatus = sessionQuery.isPending
    ? "bootstrapping"
    : !context
      ? "unauthenticated"
      : context.requires_onboarding
        ? "onboarding_required"
        : "authenticated";

  return (
    <AuthSessionContext.Provider
      value={{
        status,
        context,
        sessionAlert,
        clearSessionAlert,
        login,
        completeOnboarding,
        logout,
        rehydrateSession,
      }}
    >
      {children}
    </AuthSessionContext.Provider>
  );
}

export function useAuthSession(): AuthSessionContextValue {
  const value = useContext(AuthSessionContext);
  if (!value) {
    throw new Error("useAuthSession debe usarse dentro de AuthSessionProvider.");
  }
  return value;
}
