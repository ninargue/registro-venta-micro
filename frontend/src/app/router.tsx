import { createBrowserRouter, Navigate } from "react-router";
import type { RouteObject } from "react-router";
import { CounterShellContainer } from "@/features/auth/containers/CounterShellContainer";
import { LoginContainer } from "@/features/auth/containers/LoginContainer";

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
    path: "*",
    element: <Navigate to="/" replace />,
  },
];

export const router = createBrowserRouter(routes);
