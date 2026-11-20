import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { CatalogEmptyState } from "@/features/catalog/components/CatalogEmptyState";
import { CatalogOfflineBanner } from "@/features/catalog/components/CatalogOfflineBanner";
import { ProductGrid } from "@/features/catalog/components/ProductGrid";
import { ProductSearchBar } from "@/features/catalog/components/ProductSearchBar";
import { useOfflineProducts } from "@/features/catalog/hooks/useOfflineProducts";
import { useProducts } from "@/features/catalog/hooks/useProducts";
import { CatalogPage } from "@/features/catalog/pages/CatalogPage";
import { Button } from "@/shared/ui/Button";
import { ErrorAlert } from "@/shared/ui/ErrorAlert";

export function CatalogListContainer() {
  const navigate = useNavigate();

  const [searchText, setSearchText] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const handleOnline = () => {
      setIsOffline(false);
    };
    const handleOffline = () => {
      setIsOffline(true);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const handleSearchChange = useCallback((value: string) => {
    setSearchText(value);

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(value);
    }, 300);
  }, []);

  const params = debouncedSearch ? { q: debouncedSearch } : {};
  const { data, isLoading, isError, error, refetch } = useProducts(params);
  const offlineProducts = useOfflineProducts();

  const products = isOffline && !data ? (offlineProducts ?? []) : (data?.items ?? []);

  const handleAddProduct = () => {
    void navigate("/catalog/new");
  };

  const handleEditProduct = (id: string) => {
    void navigate(`/catalog/${id}/edit`);
  };

  if (isLoading && !isOffline) {
    return (
      <CatalogPage onAddProduct={handleAddProduct} isLoading={isLoading}>
        <div role="status" aria-label="Cargando productos" className="flex justify-center py-16">
          <span
            aria-hidden="true"
            className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--color-primary)] border-t-transparent"
          />
        </div>
      </CatalogPage>
    );
  }

  if (isError && !isOffline) {
    return (
      <CatalogPage onAddProduct={handleAddProduct}>
        <div className="flex flex-col gap-4">
          <ErrorAlert message={error.message} />
          <Button
            variant="secondary"
            onClick={() => {
              void refetch();
            }}
          >
            Reintentar
          </Button>
        </div>
      </CatalogPage>
    );
  }

  return (
    <CatalogPage onAddProduct={handleAddProduct} isOffline={isOffline}>
      <div className="flex flex-col gap-4">
        <CatalogOfflineBanner isOffline={isOffline} />

        <ProductSearchBar value={searchText} onChange={handleSearchChange} disabled={isOffline} />

        {products.length === 0 ? (
          <CatalogEmptyState />
        ) : (
          <ProductGrid products={products} onEdit={handleEditProduct} disabled={isOffline} />
        )}
      </div>
    </CatalogPage>
  );
}
