/**
 * DTOs para el módulo de catálogo — trazabilidad 1:1 con docs/api/openapi.json
 */

// ProductCreate — POST /api/v1/catalog/products requestBody
export interface ProductCreate {
  code?: string | null;
  name: string;
  sale_price: string | number;
  cost_price?: string | number;
  stock?: string | number;
}

// ProductUpdate — PATCH /api/v1/catalog/products/{product_id} requestBody
export interface ProductUpdate {
  code?: string | null;
  name?: string | null;
  sale_price?: string | number | null;
  cost_price?: string | number | null;
  stock?: string | number | null;
}

// ProductResponse — respuesta de POST (201), PATCH (200) y cada item en GET (200)
export interface ProductResponse {
  id: string;
  code: string | null;
  name: string;
  sale_price: string;
  cost_price: string | null;
  stock: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ProductListResponse — respuesta de GET /api/v1/catalog/products
export interface ProductListResponse {
  items: ProductResponse[];
  total: number;
  limit: number;
  offset: number;
}

// Parámetros de query para listado
export interface ProductListParams {
  q?: string | null;
  include_inactive?: boolean;
  limit?: number;
  offset?: number;
}

// Errores de campo client-side
export type FieldErrors = Record<string, string>;
