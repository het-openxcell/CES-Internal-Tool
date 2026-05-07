import { describe, expect, it } from "vitest";

import { authToken } from "@/lib/auth";
import { TestJwtFactory } from "@/test/test-utils";

describe("authToken", () => {
  it("stores and returns a usable token", () => {
    const token = TestJwtFactory.tokenWithExpiration(Math.floor(Date.now() / 1000) + 3600);

    authToken.store(token);

    expect(authToken.get()).toBe(token);
  });

  it("clears malformed tokens", () => {
    authToken.store("bad-token");

    expect(authToken.get()).toBeNull();
    expect(localStorage.getItem("ces.auth.token")).toBeNull();
  });

  it("clears tokens with non-numeric expiration", () => {
    const token = [
      btoa(JSON.stringify({ alg: "HS256", typ: "JWT" })),
      btoa(JSON.stringify({ exp: "not-a-number", user_id: 1 })),
      "signature",
    ].join(".");

    authToken.store(token);

    expect(authToken.get()).toBeNull();
    expect(localStorage.getItem("ces.auth.token")).toBeNull();
  });

  it("clears expired tokens", () => {
    authToken.store(TestJwtFactory.tokenWithExpiration(Math.floor(Date.now() / 1000) - 60));

    expect(authToken.get()).toBeNull();
    expect(localStorage.getItem("ces.auth.token")).toBeNull();
  });
});
