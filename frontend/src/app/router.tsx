import { lazy, Suspense } from "react";
import { createBrowserRouter, Navigate } from "react-router";
import type { RouteObject } from "react-router";
import { CounterShellContainer } from "@/features/auth/containers/CounterShellContainer";
import { LoginContainer } from "@/features/auth/containers/LoginContainer";

// eslint-disable-next-line react-refresh/only-export-components
const LazyCatalogListContainer = lazy(() =>
  import("@/features/catalog/containers/CatalogListContainer").then((m) => ({
    default: m.CatalogListContainer,
  })),
);

// eslint-disable-next-line react-refresh/only-export-components
const LazyProductCreateContainer = lazy(() =>
  import("@/features/catalog/containers/ProductCreateContainer").then((m) => ({
    default: m.ProductCreateContainer,
  })),
);

// eslint-disable-next-line react-refresh/only-export-components
const LazyProductEditContainer = lazy(() =>
  import("@/features/catalog/containers/ProductEditContainer").then((m) => ({
    default: m.ProductEditContainer,
  })),
);

export const routes: RouteObject[] = [
  {
    path: "/login",
    element: <LoginContainer />,
  },
  {
    path: "/",
    element: <CounterShellContainer />,
  },
  {
    path: "/catalog",
    element: (
      <Suspense fallback={<div role="status" aria-label="Cargando catálogo" />}>
        <LazyCatalogListContainer />
      </Suspense>
    ),
  },
  {
    path: "/catalog/new",
    element: (
      <Suspense fallback={<div role="status" aria-label="Cargando formulario" />}>
        <LazyProductCreateContainer />
      </Suspense>
    ),
  },
  {
    path: "/catalog/:productId/edit",
    element: (
      <Suspense fallback={<div role="status" aria-label="Cargando producto" />}>
        <LazyProductEditContainer />
      </Suspense>
    ),
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
];

export const router = createBrowserRouter(routes);
