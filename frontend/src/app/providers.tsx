import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

const defaultQueryClient = new QueryClient();

export interface ProvidersProps {
  children: ReactNode;
  queryClient?: QueryClient;
}

export function Providers({ children, queryClient = defaultQueryClient }: ProvidersProps) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
