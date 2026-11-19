import { useEffect, useState } from "react";
import { db } from "@/lib/db";
import type { ProductResponse } from "@/features/catalog/types";

/**
 * Lee todos los productos desde Dexie (IndexedDB) para modo offline.
 * Se actualiza reactivamente cuando la tabla cambia.
 */
export function useOfflineProducts(): ProductResponse[] | undefined {
  const [products, setProducts] = useState<ProductResponse[] | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const items = await db.products.toArray();
        if (!cancelled) {
          setProducts(items);
        }
      } catch {
        // IndexedDB not available (e.g., in JSDOM tests) — return empty array
        if (!cancelled) {
          setProducts([]);
        }
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  return products;
}
