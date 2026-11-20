import type { ReactNode } from "react";

export interface ProductNewPageProps {
  children: ReactNode;
}

export function ProductNewPage({ children }: ProductNewPageProps) {
  return (
    <main className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold text-[var(--color-text-light)] dark:text-[var(--color-text-dark)]">
        Nuevo producto
      </h1>
      {children}
    </main>
  );
}
