import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateProduct } from "@/features/catalog/api";
import type { ProductResponse, ProductUpdate } from "@/features/catalog/types";

interface UpdateProductVariables {
  id: string;
  payload: ProductUpdate;
}

export function useUpdateProduct() {
  const queryClient = useQueryClient();

  return useMutation<ProductResponse, Error, UpdateProductVariables>({
    mutationFn: ({ id, payload }) => updateProduct(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["catalog", "products"] });
    },
  });
}
