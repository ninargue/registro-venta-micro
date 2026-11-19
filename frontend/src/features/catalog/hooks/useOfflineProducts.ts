import { useLiveQuery } from "dexie-react-hooks";
import { db } from "@/lib/db";
import type { ProductResponse } from "@/features/catalog/types";

/**
 * Lee todos los productos desde Dexie (IndexedDB) para modo offline.
 */
export function useOfflineProducts(): ProductResponse[] | undefined {
  return useLiveQuery(() => db.products.toArray());
}
