import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { AuthSessionProvider } from "@/features/auth/AuthContext";
import { ThemeProvider } from "@/features/auth/ThemeContext";

const defaultQueryClient = new QueryClient();

export interface ProvidersProps {
  children: ReactNode;
  queryClient?: QueryClient;
}

export function Providers({ children, queryClient = defaultQueryClient }: ProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthSessionProvider>{children}</AuthSessionProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
