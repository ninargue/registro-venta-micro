import { apiFetch } from "@/lib/api-client";
import type {
  ProductCreate,
  ProductListParams,
  ProductListResponse,
  ProductResponse,
  ProductUpdate,
} from "@/features/catalog/types";

export function fetchProducts(params: ProductListParams): Promise<ProductListResponse> {
  const searchParams = new URLSearchParams();

  if (params.q) {
    searchParams.set("q", params.q);
  }
  if (params.include_inactive !== undefined) {
    searchParams.set("include_inactive", String(params.include_inactive));
  }
  if (params.limit !== undefined) {
    searchParams.set("limit", String(params.limit));
  }
  if (params.offset !== undefined) {
    searchParams.set("offset", String(params.offset));
  }

  const qs = searchParams.toString();
  const url = `/api/v1/catalog/products${qs ? `?${qs}` : ""}`;

  return apiFetch<ProductListResponse>(url, { method: "GET" });
}

export function createProduct(payload: ProductCreate): Promise<ProductResponse> {
  return apiFetch<ProductResponse>("/api/v1/catalog/products", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateProduct(id: string, payload: ProductUpdate): Promise<ProductResponse> {
  return apiFetch<ProductResponse>(`/api/v1/catalog/products/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
