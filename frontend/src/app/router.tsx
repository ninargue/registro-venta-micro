import { createBrowserRouter, Navigate } from "react-router";
import type { RouteObject } from "react-router";
import { CounterShellContainer } from "@/features/auth/containers/CounterShellContainer";
import { LoginContainer } from "@/features/auth/containers/LoginContainer";

import { DailyReportPage } from "@/features/reports/pages/DailyReportPage";

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
  {
    path: "/reports/daily",
    element: <DailyReportPage />,
  },
];

export const router = createBrowserRouter(routes);
