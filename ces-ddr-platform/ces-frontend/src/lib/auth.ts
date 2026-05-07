const TOKEN_KEY = "ces.auth.token";

type JwtPayload = {
  exp?: unknown;
};

class AuthToken {
  store(token: string) {
    localStorage.setItem(TOKEN_KEY, token);
  }

  get() {
    const token = localStorage.getItem(TOKEN_KEY);

    if (!token || this.isExpiredOrMalformed(token)) {
      this.clear();
      return null;
    }

    return token;
  }

  clear() {
    localStorage.removeItem(TOKEN_KEY);
  }

  isAuthenticated() {
    return this.get() !== null;
  }

  private isExpiredOrMalformed(token: string) {
    const payload = this.decodePayload(token);

    if (typeof payload?.exp !== "number" || !Number.isFinite(payload.exp)) {
      return true;
    }

    return payload.exp <= Math.floor(Date.now() / 1000);
  }

  private decodePayload(token: string): JwtPayload | null {
    const parts = token.split(".");

    if (parts.length !== 3) {
      return null;
    }

    try {
      const normalized = parts[1].replaceAll("-", "+").replaceAll("_", "/");
      const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
      return JSON.parse(atob(padded)) as JwtPayload;
    } catch {
      return null;
    }
  }
}

export const authToken = new AuthToken();
