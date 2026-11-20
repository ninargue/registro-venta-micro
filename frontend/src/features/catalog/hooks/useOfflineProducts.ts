import { liveQuery } from "dexie";
import { useEffect, useState } from "react";
import { db } from "@/lib/db";
import type { ProductResponse } from "@/features/catalog/types";

/**
 * Lee todos los productos desde Dexie (IndexedDB) para modo offline.
 * Usa liveQuery para reactividad real: se actualiza automáticamente
 * ante cualquier escritura en la tabla (otras pestañas, service worker).
 */
export function useOfflineProducts(): ProductResponse[] | undefined {
  const [products, setProducts] = useState<ProductResponse[] | undefined>(undefined);

  useEffect(() => {
    const subscription = liveQuery(() => db.products.toArray()).subscribe({
      next: (items) => setProducts(items as ProductResponse[]),
      error: () => {
        // IndexedDB not available (e.g., in JSDOM tests) — return empty array
        setProducts([]);
      },
    });

    return () => subscription.unsubscribe();
  }, []);

  return products;
}
