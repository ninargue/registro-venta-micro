import { useState, type SyntheticEvent } from "react";
import { Button } from "@/shared/ui/Button";
import { ErrorAlert } from "@/shared/ui/ErrorAlert";
import { TextField } from "@/shared/ui/TextField";
import type { FieldErrors, ProductCreate, ProductResponse, ProductUpdate } from "@/features/catalog/types";

export interface ProductFormProps {
  mode: "create" | "edit";
  initialValues?: Partial<ProductResponse>;
  onSubmit: (data: ProductCreate | ProductUpdate) => void;
  onCancel: () => void;
  isLoading?: boolean;
  errorMessage?: string | null;
  fieldErrors?: FieldErrors | null;
}

export function ProductForm({
  mode,
  initialValues,
  onSubmit,
  onCancel,
  isLoading = false,
  errorMessage,
  fieldErrors,
}: ProductFormProps) {
  const [name, setName] = useState<string>(initialValues?.name ?? "");
  const [salePrice, setSalePrice] = useState<string>(initialValues?.sale_price ?? "");
  const [code, setCode] = useState<string>(initialValues?.code ?? "");
  const [costPrice, setCostPrice] = useState<string>(initialValues?.cost_price ?? "");
  const [stock, setStock] = useState<string>(initialValues?.stock ?? "");

  const submitLabel = mode === "create" ? "Agregar producto" : "Guardar cambios";

  const handleSubmit = (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    const data: ProductCreate | ProductUpdate = {
      name: name.trim() || undefined,
      sale_price: salePrice !== "" ? salePrice : undefined,
      code: code.trim() !== "" ? code.trim() : null,
      cost_price: costPrice !== "" ? costPrice : undefined,
      stock: stock !== "" ? stock : undefined,
    };
    onSubmit(data);
  };

  const hasNameError = fieldErrors?.["name"] !== undefined;
  const hasPriceError = fieldErrors?.["sale_price"] !== undefined;

  const firstError =
    errorMessage ??
    (fieldErrors ? Object.values(fieldErrors)[0] : null) ??
    null;

  return (
    <form
      onSubmit={handleSubmit}
      aria-busy={isLoading || undefined}
      noValidate
      className="flex flex-col gap-4"
    >
      <ErrorAlert message={firstError} />

      <TextField
        id="product-name"
        label="Nombre"
        value={name}
        onChange={(e) => { setName(e.target.value); }}
        required
        hasError={hasNameError}
        aria-invalid={hasNameError ? true : undefined}
        helperText={fieldErrors?.["name"]}
        disabled={isLoading}
      />

      <TextField
        id="product-sale-price"
        label="Precio de venta"
        type="text"
        inputMode="decimal"
        value={salePrice}
        onChange={(e) => { setSalePrice(e.target.value); }}
        required
        hasError={hasPriceError}
        aria-invalid={hasPriceError ? true : undefined}
        helperText={fieldErrors?.["sale_price"]}
        disabled={isLoading}
      />

      <TextField
        id="product-code"
        label="Código SKU"
        value={code}
        onChange={(e) => { setCode(e.target.value); }}
        disabled={isLoading}
      />

      <TextField
        id="product-cost-price"
        label="Costo"
        type="text"
        inputMode="decimal"
        value={costPrice}
        onChange={(e) => { setCostPrice(e.target.value); }}
        disabled={isLoading}
      />

      <TextField
        id="product-stock"
        label="Stock"
        type="text"
        inputMode="decimal"
        value={stock}
        onChange={(e) => { setStock(e.target.value); }}
        disabled={isLoading}
      />

      <div className="flex gap-3">
        <Button
          type="submit"
          variant="primary"
          isLoading={isLoading}
          disabled={isLoading}
          aria-busy={isLoading || undefined}
        >
          {submitLabel}
        </Button>

        <Button
          type="button"
          variant="secondary"
          onClick={onCancel}
          disabled={isLoading}
        >
          Cancelar
        </Button>
      </div>
    </form>
  );
}
