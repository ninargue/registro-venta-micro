import type { ReactNode } from "react";
import { Button } from "@/shared/ui/Button";

export interface CatalogPageProps {
  children: ReactNode;
  onAddProduct: () => void;
  isLoading?: boolean;
  isOffline?: boolean;
}

export function CatalogPage({ children, onAddProduct, isLoading = false, isOffline = false }: CatalogPageProps) {
  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-[var(--color-text-light)] dark:text-[var(--color-text-dark)]">
          Catálogo de productos
        </h1>

        <Button
          variant="primary"
          onClick={onAddProduct}
          disabled={isLoading || isOffline}
          aria-label="Agregar producto"
        >
          Agregar producto
        </Button>
      </div>

      {children}
    </main>
  );
}
