import { ProductCard } from "@/features/catalog/components/ProductCard";
import type { ProductResponse } from "@/features/catalog/types";

export interface ProductGridProps {
  products: ProductResponse[];
  onEdit: (id: string) => void;
  disabled?: boolean;
}

export function ProductGrid({ products, onEdit, disabled = false }: ProductGridProps) {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Lista de productos">
      {products.map((product) => (
        <li key={product.id}>
          <ProductCard product={product} onEdit={onEdit} disabled={disabled} />
        </li>
      ))}
    </ul>
  );
}
