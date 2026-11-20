import Dexie, { type Table } from "dexie";
import type { ProductResponse } from "@/features/catalog/types";

class AppDatabase extends Dexie {
  products!: Table<ProductResponse>;

  constructor() {
    super("AppDatabase");
    this.version(1).stores({
      products: "id, name, is_active",
    });
  }
}

export const db = new AppDatabase();
