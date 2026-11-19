// Types
export type {
  FieldErrors,
  ProductCreate,
  ProductListParams,
  ProductListResponse,
  ProductResponse,
  ProductUpdate,
} from "@/features/catalog/types";

// API
export { createProduct, fetchProducts, updateProduct } from "@/features/catalog/api";

// Validation
export { validateProductCreate, validateProductUpdate } from "@/features/catalog/validation";

// Hooks
export { useCreateProduct } from "@/features/catalog/hooks/useCreateProduct";
export { useOfflineProducts } from "@/features/catalog/hooks/useOfflineProducts";
export { useProducts } from "@/features/catalog/hooks/useProducts";
export { useUpdateProduct } from "@/features/catalog/hooks/useUpdateProduct";

// Components
export { CatalogEmptyState } from "@/features/catalog/components/CatalogEmptyState";
export { CatalogOfflineBanner } from "@/features/catalog/components/CatalogOfflineBanner";
export { ProductCard } from "@/features/catalog/components/ProductCard";
export { ProductForm } from "@/features/catalog/components/ProductForm";
export { ProductGrid } from "@/features/catalog/components/ProductGrid";
export { ProductSearchBar } from "@/features/catalog/components/ProductSearchBar";

// Pages
export { CatalogPage } from "@/features/catalog/pages/CatalogPage";
export { ProductEditPage } from "@/features/catalog/pages/ProductEditPage";
export { ProductNewPage } from "@/features/catalog/pages/ProductNewPage";

// Containers
export { CatalogListContainer } from "@/features/catalog/containers/CatalogListContainer";
export { ProductCreateContainer } from "@/features/catalog/containers/ProductCreateContainer";
export { ProductEditContainer } from "@/features/catalog/containers/ProductEditContainer";
