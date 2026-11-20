import type { FieldErrors, ProductCreate, ProductUpdate } from "@/features/catalog/types";

/**
 * Valida los datos del formulario de alta de producto antes de enviar al servidor.
 * Retorna un objeto con errores de campo, o null si no hay errores.
 */
export function validateProductCreate(data: Partial<ProductCreate>): FieldErrors | null {
  const errors: FieldErrors = {};

  const name = typeof data.name === "string" ? data.name.trim() : "";
  if (name.length === 0) {
    errors["name"] = "El nombre del producto es obligatorio.";
  } else if (name.length > 150) {
    errors["name"] = "El nombre no puede superar los 150 caracteres.";
  }

  const salePrice = Number(data.sale_price);
  if (data.sale_price === undefined || data.sale_price === "") {
    errors["sale_price"] = "El precio de venta es obligatorio.";
  } else if (isNaN(salePrice) || salePrice <= 0) {
    errors["sale_price"] = "El precio de venta debe ser mayor que cero.";
  }

  return Object.keys(errors).length > 0 ? errors : null;
}

/**
 * Valida los datos del formulario de edición de producto.
 * Solo valida los campos que están presentes.
 */
export function validateProductUpdate(data: Partial<ProductUpdate>): FieldErrors | null {
  const errors: FieldErrors = {};

  if (data.name !== undefined && data.name !== null) {
    const name = typeof data.name === "string" ? data.name.trim() : "";
    if (name.length === 0) {
      errors["name"] = "El nombre del producto es obligatorio.";
    } else if (name.length > 150) {
      errors["name"] = "El nombre no puede superar los 150 caracteres.";
    }
  }

  if (data.sale_price !== undefined && data.sale_price !== null) {
    const salePrice = Number(data.sale_price);
    if (isNaN(salePrice) || salePrice <= 0) {
      errors["sale_price"] = "El precio de venta debe ser mayor que cero.";
    }
  }

  return Object.keys(errors).length > 0 ? errors : null;
}
