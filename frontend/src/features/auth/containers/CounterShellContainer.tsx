import { lazy, Suspense, useState } from "react";
import { Navigate, useNavigate } from "react-router";
import { CounterShellPage } from "@/app/CounterShellPage";
import { useAuthSession } from "@/features/auth/AuthContext";
import { useTheme } from "@/features/auth/ThemeContext";

const LazyOnboardingContainer = lazy(() =>
  import("@/features/auth/containers/OnboardingContainer").then((module) => ({
    default: module.OnboardingContainer,
  })),
);

export function CounterShellContainer() {
  const navigate = useNavigate();
  const { status, context, logout } = useAuthSession();
  const { isDark, toggleTheme } = useTheme();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const performLogout = async () => {
    if (isLoggingOut) {
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

  if (status === "bootstrapping") {
    return <CounterShellPage isLoading isDark={isDark} onToggleTheme={toggleTheme} />;
  }

  if (status === "unauthenticated") {
    return <Navigate to="/login" replace />;
  }

  if (status === "onboarding_required") {
    return (
      <>
        <CounterShellPage
          userEmail={context?.user.email ?? null}
          isDark={isDark}
          onToggleTheme={toggleTheme}
          isLoggingOut={isLoggingOut}
          onLogout={handleLogout}
        />
        <Suspense fallback={null}>
          <LazyOnboardingContainer allowLogout />
        </Suspense>
      </>
    );
  }

  return (
    <CounterShellPage
      businessName={context?.business?.name ?? null}
      userEmail={context?.user.email ?? null}
      country={context?.business?.country ?? null}
      timezone={context?.business?.timezone ?? null}
      isLoggingOut={isLoggingOut}
      onLogout={handleLogout}
      isDark={isDark}
      onToggleTheme={toggleTheme}
    />
  );
}
