export interface CatalogOfflineBannerProps {
  isOffline: boolean;
}

export function CatalogOfflineBanner({ isOffline }: CatalogOfflineBannerProps) {
  if (!isOffline) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={[
        "rounded-[var(--radius-control)] border px-4 py-3 text-sm font-medium",
        "border-[var(--color-border-light)] dark:border-[var(--color-border-dark)]",
        "bg-[var(--color-primary-light)] text-[var(--color-text-light)] dark:text-[var(--color-text-dark)]",
      ].join(" ")}
    >
      Mostrando datos guardados — sin conexión a Internet
    </div>
  );
}
