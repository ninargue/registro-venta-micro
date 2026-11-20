import type { ReactNode } from "react";
import { NavLink } from "react-router";

export interface AppNavigationItem {
  to: string;
  label: string;
  icon: ReactNode;
  /** Coincidencia exacta de ruta (necesaria para "/" que prefija a todas las demás). */
  end?: boolean;
}

export interface AppNavigationProps {
  items: AppNavigationItem[];
}

const BASE_LINK_CLASSES = [
  "touch-target flex flex-1 flex-col items-center justify-center gap-1 rounded-[var(--radius-control)] px-3 py-2 text-xs font-medium transition-colors",
  "md:flex-none md:flex-row md:justify-start md:gap-3 md:text-sm",
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
].join(" ");

const ACTIVE_LINK_CLASSES =
  "bg-[var(--color-primary-light)] text-[var(--color-primary-dark)] dark:bg-[var(--color-primary-dark)] dark:text-[var(--color-text-dark)]";

const IDLE_LINK_CLASSES =
  "text-[var(--color-text-muted-light)] hover:bg-[var(--color-background-light)] dark:text-[var(--color-text-muted-dark)] dark:hover:bg-[var(--color-background-dark)]";

/**
 * Navegación principal persistente: barra inferior en móvil y barra lateral desde `md`.
 * Usa NavLink, que expone `aria-current="page"` en la entrada activa.
 */
export function AppNavigation({ items }: AppNavigationProps) {
  return (
    <nav
      aria-label="Navegación principal"
      className={[
        "fixed inset-x-0 bottom-0 z-40 border-t border-[var(--color-border-light)] bg-[var(--color-surface-light)] p-2",
        "dark:border-[var(--color-border-dark)] dark:bg-[var(--color-surface-dark)]",
        "md:inset-y-0 md:right-auto md:w-56 md:border-t-0 md:border-r md:p-4",
      ].join(" ")}
    >
      <ul className="flex items-stretch gap-1 md:flex-col">
        {items.map((item) => (
          <li key={item.to} className="flex flex-1 md:flex-none">
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `${BASE_LINK_CLASSES} w-full ${isActive ? ACTIVE_LINK_CLASSES : IDLE_LINK_CLASSES}`
              }
            >
              <span aria-hidden="true" className="inline-flex h-6 w-6 items-center justify-center">
                {item.icon}
              </span>
              <span>{item.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
