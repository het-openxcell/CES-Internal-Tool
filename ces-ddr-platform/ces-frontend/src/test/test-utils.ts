export class TestJwtFactory {
  static tokenWithExpiration(expiresAtSeconds: number) {
    return [
      this.encode({ alg: "HS256", typ: "JWT" }),
      this.encode({ exp: expiresAtSeconds, user_id: 1 }),
      "signature",
    ].join(".");
  }

  private static encode(value: Record<string, unknown>) {
    return btoa(JSON.stringify(value)).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
  }
}
