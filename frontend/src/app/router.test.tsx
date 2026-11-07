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
