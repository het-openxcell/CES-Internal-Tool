import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/lib/api";
import { authToken } from "@/lib/auth";
import { TestJwtFactory } from "@/test/test-utils";
import apiSource from "./api.ts?raw";

describe("apiClient", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("posts login credentials to VITE_API_URL auth endpoint", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ token: "jwt-token", expires_at: 1778158800 }), { status: 200 }),
    );

    await apiClient.login({ username: "operator", password: "secret" });

    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ username: "operator", password: "secret" }),
      }),
    );
  });

  it("injects bearer token on shared requests", async () => {
    const token = TestJwtFactory.tokenWithExpiration(Math.floor(Date.now() / 1000) + 3600);
    authToken.store(token);
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    await apiClient.request("/reports/1");

    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/reports/1",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: `Bearer ${token}`,
        }),
      }),
    );
  });

  it("clears token and redirects to login on 401", async () => {
    authToken.store(TestJwtFactory.tokenWithExpiration(Math.floor(Date.now() / 1000) + 3600));
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401 }));

    await expect(apiClient.request("/history")).rejects.toMatchObject({ code: "UNAUTHORIZED" });

    expect(authToken.get()).toBeNull();
    expect(window.location.pathname).toBe("/login");
  });

  it("returns undefined for empty successful responses", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }));

    await expect(apiClient.request("/history")).resolves.toBeUndefined();
  });

  it("reads base URL from VITE_API_URL without hardcoded backend URL", () => {
    expect(apiSource).toContain("import.meta.env.VITE_API_URL");
    expect(apiSource).not.toMatch(/https?:\/\//);
    expect(apiSource).not.toContain("localhost");
  });
});
