import { createBrowserRouter } from "react-router";
import type { RouteObject } from "react-router";

import { DailyReportPage } from "@/features/reports/pages/DailyReportPage";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <h1>registro-venta-micro</h1>,
  },
  {
    path: "/reports/daily",
    element: <DailyReportPage />,
  },
];

export const router = createBrowserRouter(routes);
