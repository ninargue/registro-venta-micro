import type { ReactNode } from "react";
import { Outlet } from "react-router";
import { useAuthSession } from "@/features/auth/AuthContext";
import { AppNavigation } from "@/shared/ui/AppNavigation";
import type { AppNavigationItem } from "@/shared/ui/AppNavigation";

function NavIcon({ children }: { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="22"
      height="22"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

const NAVIGATION_ITEMS: AppNavigationItem[] = [
  {
    to: "/",
    label: "Inicio",
    end: true,
    icon: (
      <NavIcon>
        <path d="M3 11l9-8 9 8" />
        <path d="M5 10v10h14V10" />
      </NavIcon>
    ),
  },
  {
    to: "/catalog",
    label: "Catálogo",
    icon: (
      <NavIcon>
        <path d="M21 8l-9-5-9 5 9 5 9-5z" />
        <path d="M3 8v8l9 5 9-5V8" />
      </NavIcon>
    ),
  },
  {
    to: "/reports/daily",
    label: "Reporte diario",
    icon: (
      <NavIcon>
        <path d="M4 20V10" />
        <path d="M10 20V4" />
        <path d="M16 20v-8" />
        <path d="M22 20H2" />
      </NavIcon>
    ),
  },
];

/**
 * Layout de las rutas de la aplicación. Muestra la navegación persistente solo con
 * sesión activa y negocio configurado; en cualquier otro estado renderiza la ruta sola.
 */
export function AppLayout() {
  const { status } = useAuthSession();

  if (status !== "authenticated") {
    return <Outlet />;
  }

  return (
    <>
      <AppNavigation items={NAVIGATION_ITEMS} />
      <div className="pb-24 md:pb-0 md:pl-56">
        <Outlet />
      </div>
    </>
  );
}
