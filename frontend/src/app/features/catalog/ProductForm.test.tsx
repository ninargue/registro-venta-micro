import { createEvent, fireEvent, render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProductForm } from "@/features/catalog/components/ProductForm";

describe("ProductForm — submit", () => {
  it("previene el envío nativo del formulario (preventDefault)", () => {
    const onSubmit = vi.fn();
    const { container } = render(
      <ProductForm mode="create" onSubmit={onSubmit} onCancel={vi.fn()} />,
    );
    const form = container.querySelector("form") as HTMLFormElement;

    const event = createEvent.submit(form);
    fireEvent(form, event);

    expect(event.defaultPrevented).toBe(true);
    expect(onSubmit).toHaveBeenCalledOnce();
  });
});
