import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { fetchProducts } from "@/features/catalog/api";
import type { ProductListParams, ProductListResponse } from "@/features/catalog/types";
import { db } from "@/lib/db";

export function useProducts(params: ProductListParams) {
  return useQuery<ProductListResponse>({
    queryKey: ["catalog", "products", params],
    queryFn: async () => {
      const data = await fetchProducts(params);
      // Persist to Dexie for offline support
      try {
        await db.products.bulkPut(data.items);
      } catch {
        // IndexedDB not available in test environment — ignore silently
      }
      return data;
    },
    placeholderData: keepPreviousData,
  });
}
