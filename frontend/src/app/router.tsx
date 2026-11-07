import { createBrowserRouter } from "react-router";
import type { RouteObject } from "react-router";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <h1>registro-venta-micro</h1>,
  },
];

export const router = createBrowserRouter(routes);
