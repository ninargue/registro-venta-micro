import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createProduct } from "@/features/catalog/api";
import type { ProductCreate, ProductResponse } from "@/features/catalog/types";

export function useCreateProduct() {
  const queryClient = useQueryClient();

  return useMutation<ProductResponse, Error, ProductCreate>({
    mutationFn: (payload) => createProduct(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["catalog", "products"] });
    },
  });
}
