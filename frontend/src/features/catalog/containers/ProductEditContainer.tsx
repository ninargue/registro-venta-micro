import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { ProductForm } from "@/features/catalog/components/ProductForm";
import { useProducts } from "@/features/catalog/hooks/useProducts";
import { useUpdateProduct } from "@/features/catalog/hooks/useUpdateProduct";
import { ProductEditPage } from "@/features/catalog/pages/ProductEditPage";
import { validateProductUpdate } from "@/features/catalog/validation";
import type { FieldErrors, ProductCreate, ProductUpdate } from "@/features/catalog/types";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/shared/ui/Button";
import { ErrorAlert } from "@/shared/ui/ErrorAlert";

export function ProductEditContainer() {
  const navigate = useNavigate();
  const { productId } = useParams<{ productId: string }>();

  const { data: listData, isLoading: isListLoading } = useProducts({});
  const { mutate, isPending } = useUpdateProduct();

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors | null>(null);
  const [notFound, setNotFound] = useState(false);

  const product = listData?.items.find((p) => p.id === productId);

  const handleSubmit = (data: ProductCreate | ProductUpdate) => {
    if (!productId) return;

    setErrorMessage(null);
    setFieldErrors(null);

    const updatePayload: ProductUpdate = {
      name: typeof data.name === "string" ? data.name : undefined,
      sale_price: data.sale_price ?? undefined,
      code: data.code ?? undefined,
      cost_price: data.cost_price ?? undefined,
      stock: data.stock ?? undefined,
    };

    const validationErrors = validateProductUpdate(updatePayload);
    if (validationErrors) {
      setFieldErrors(validationErrors);
      const firstMsg = Object.values(validationErrors)[0] ?? "Revisa los campos del formulario.";
      setErrorMessage(firstMsg);
      return;
    }

    mutate(
      { id: productId, payload: updatePayload },
      {
        onSuccess: () => {
          void navigate("/catalog");
        },
        onError: (err) => {
          if (err instanceof ApiError) {
            if (err.status === 404) {
              setNotFound(true);
              setErrorMessage(err.message);
            } else {
              setErrorMessage(err.message);
            }
          } else {
            setErrorMessage("No se pudo conectar con el servidor. Intenta nuevamente.");
          }
        },
      },
    );
  };

  const handleCancel = () => {
    void navigate("/catalog");
  };

  if (isListLoading) {
    return (
      <ProductEditPage>
        <div role="status" aria-label="Cargando producto" className="flex justify-center py-16">
          <span
            aria-hidden="true"
            className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--color-primary)] border-t-transparent"
          />
        </div>
      </ProductEditPage>
    );
  }

  return (
    <ProductEditPage>
      {notFound ? (
        <div className="flex flex-col gap-4">
          <ErrorAlert message={errorMessage} />
          <Button variant="secondary" onClick={handleCancel}>
            Volver al catálogo
          </Button>
        </div>
      ) : (
        <ProductForm
          mode="edit"
          initialValues={product}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          isLoading={isPending}
          errorMessage={errorMessage}
          fieldErrors={fieldErrors}
        />
      )}
    </ProductEditPage>
  );
}
