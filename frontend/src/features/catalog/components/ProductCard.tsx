import { Button } from "@/shared/ui/Button";
import type { ProductResponse } from "@/features/catalog/types";

export interface ProductCardProps {
  product: ProductResponse;
  onEdit: (id: string) => void;
  disabled?: boolean;
}

export function ProductCard({ product, onEdit, disabled = false }: ProductCardProps) {
  const stockValue = Number(product.stock);
  const hasStock = stockValue > 0;

  return (
    <article
      className={[
        "flex flex-col gap-3 rounded-[var(--radius-control)] border p-4",
        "bg-[var(--color-surface-light)] dark:bg-[var(--color-surface-dark)]",
        "border-[var(--color-border-light)] dark:border-[var(--color-border-dark)]",
      ].join(" ")}
    >
      <div className="flex flex-col gap-1">
        <h3
          className="text-base font-semibold text-[var(--color-text-light)] dark:text-[var(--color-text-dark)]"
        >
          {product.name}
        </h3>
        {product.code ? (
          <span className="text-sm text-[var(--color-text-muted-light)] dark:text-[var(--color-text-muted-dark)]">
            SKU: {product.code}
          </span>
        ) : null}
      </div>

      <div className="flex items-center justify-between gap-2">
        <div className="flex flex-col gap-0.5">
          <span
            className="text-lg font-bold text-[var(--color-text-light)] dark:text-[var(--color-text-dark)]"
          >
            {product.sale_price}
          </span>
          <span
            className="text-sm"
            style={{ color: hasStock ? "var(--color-success)" : "var(--color-error)" }}
          >
            Stock: {product.stock}
          </span>
        </div>

        <Button
          variant="secondary"
          onClick={() => { onEdit(product.id); }}
          aria-label={`Editar ${product.name}`}
          disabled={disabled}
        >
          Editar
        </Button>
      </div>
    </article>
  );
}
