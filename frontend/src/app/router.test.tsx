import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { expect, test } from "vitest";

import { Providers } from "@/app/providers";
import { routes } from "@/app/router";

test('la ruta "/" muestra el h1 con el nombre del producto', () => {
  const router = createMemoryRouter(routes, { initialEntries: ["/"] });

  render(
    <Providers>
      <RouterProvider router={router} />
    </Providers>,
  );

  expect(
    screen.getByRole("heading", { level: 1, name: "registro-venta-micro" }),
  ).toBeInTheDocument();
});

test('Scenario: Owner views daily report with sales and positive gross margin (state: ready) — la ruta "/reports/daily" monta la vista de reporte diario y muestra los KPIs', async () => {
  const router = createMemoryRouter(routes, {
    initialEntries: ["/reports/daily"],
  });

  render(
    <Providers>
      <RouterProvider router={router} />
    </Providers>,
  );

  expect(
    await screen.findByRole("heading", {
      level: 1,
      name: "Reporte Diario de Ventas y Margen",
    }),
  ).toBeInTheDocument();

  expect(await screen.findByText("$30.000,00")).toBeInTheDocument();
  expect(screen.getByText("$9.000,00")).toBeInTheDocument();
  expect(screen.getByText("$21.000,00")).toBeInTheDocument();
});
