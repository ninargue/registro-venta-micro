import { useState } from "react";
import { useNavigate } from "react-router";
import { ProductForm } from "@/features/catalog/components/ProductForm";
import { useCreateProduct } from "@/features/catalog/hooks/useCreateProduct";
import { ProductNewPage } from "@/features/catalog/pages/ProductNewPage";
import { validateProductCreate } from "@/features/catalog/validation";
import type { FieldErrors, ProductCreate, ProductUpdate } from "@/features/catalog/types";
import { ApiError } from "@/lib/api-client";

export function ProductCreateContainer() {
  const navigate = useNavigate();
  const { mutate, isPending } = useCreateProduct();

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors | null>(null);

  const handleSubmit = (data: ProductCreate | ProductUpdate) => {
    setErrorMessage(null);
    setFieldErrors(null);

    const payload = data as ProductCreate;
    const validationErrors = validateProductCreate(payload);
    if (validationErrors) {
      setFieldErrors(validationErrors);
      const firstMsg = Object.values(validationErrors)[0] ?? "Revisa los campos del formulario.";
      setErrorMessage(firstMsg);
      return;
    }

    mutate(payload, {
      onSuccess: () => {
        void navigate("/catalog");
      },
      onError: (err) => {
        if (err instanceof ApiError) {
          setErrorMessage(err.message);
        } else {
          setErrorMessage("No se pudo conectar con el servidor. Intenta nuevamente.");
        }
      },
    });
  };

  const handleCancel = () => {
    void navigate("/catalog");
  };

  return (
    <ProductNewPage>
      <ProductForm
        mode="create"
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        isLoading={isPending}
        errorMessage={errorMessage}
        fieldErrors={fieldErrors}
      />
    </ProductNewPage>
  );
}
