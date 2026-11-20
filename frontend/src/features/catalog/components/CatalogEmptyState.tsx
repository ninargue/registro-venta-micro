export function CatalogEmptyState() {
  return (
    <div className="flex flex-col items-center gap-6 py-16 text-center" aria-label="Catálogo vacío">
      <div className="flex flex-col gap-2">
        <p className="text-lg font-semibold text-[var(--color-text-light)] dark:text-[var(--color-text-dark)]">
          No hay productos en el catálogo
        </p>
        <p className="text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted-dark)]">
          Usa el botón "Agregar producto" para comenzar.
        </p>
      </div>
    </div>
  );
}
