import { describe, expect, it } from "vitest";

describe("MSW mock server (server.ts)", () => {
  it("intercepta peticiones GET a /api/v1/health y responde json healthy", async () => {
    const response = await fetch("/api/v1/health");
    expect(response.status).toBe(200);

    const body = (await response.json()) as { status: string };
    expect(body).toEqual({ status: "healthy" });
  });
});
