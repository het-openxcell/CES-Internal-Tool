import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "@/App";
import { REQUIRED_ROUTES } from "@/routes";
import { authToken } from "@/lib/auth";
import { TestJwtFactory } from "@/test/test-utils";

describe("App routing and login", () => {
  it("redirects unauthenticated protected routes to login", async () => {
    window.history.pushState({}, "", "/history");

    render(<App />);

    expect(await screen.findByLabelText("Username")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/login");
  });

  it("stores token and navigates to dashboard after valid login", async () => {
    const token = TestJwtFactory.tokenWithExpiration(Math.floor(Date.now() / 1000) + 3600);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ token, expires_at: 1778158800 }), { status: 200 }),
      ),
    );
    window.history.pushState({}, "", "/login");

    render(<App />);

    await userEvent.type(screen.getByLabelText("Username"), "operator");
    await userEvent.type(screen.getByLabelText("Password"), "secret");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(window.location.pathname).toBe("/"));
    expect(authToken.get()).toBe(token);
    expect(screen.getByRole("heading", { name: "DDR Operations Console" })).toBeInTheDocument();
  });

  it("shows safe invalid-credential copy, clears password, and keeps username", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: "Invalid credentials", code: "UNAUTHORIZED", details: {} }), {
          status: 401,
        }),
      ),
    );
    window.history.pushState({}, "", "/login");

    render(<App />);

    await userEvent.type(screen.getByLabelText("Username"), "operator");
    await userEvent.type(screen.getByLabelText("Password"), "bad");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Invalid username or password")).toBeInTheDocument();
    expect(screen.getByLabelText("Username")).toHaveValue("operator");
    expect(screen.getByLabelText("Password")).toHaveValue("");
  });

  it("declares all required routes and protects each route except login", () => {
    expect(REQUIRED_ROUTES).toEqual([
      { path: "/login", protected: false },
      { path: "/", protected: true },
      { path: "/reports/:id", protected: true },
      { path: "/history", protected: true },
      { path: "/query", protected: true },
      { path: "/monitor", protected: true },
      { path: "/settings/keywords", protected: true },
    ]);
  });
});
