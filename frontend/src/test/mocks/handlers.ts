import { http, HttpResponse } from "msw";

export const handlers = [
  // Handler base para health check
  http.get("/api/v1/health", () => {
    return HttpResponse.json({ status: "healthy" });
  }),
];
