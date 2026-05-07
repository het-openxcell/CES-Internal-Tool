import { authToken } from "@/lib/auth";

export type LoginCredentials = {
  username: string;
  password: string;
};

export type LoginResponse = {
  token: string;
  expires_at: number;
};

export type ApiErrorCode = "UNAUTHORIZED" | "API_ERROR";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: ApiErrorCode,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

class ApiClient {
  private readonly baseUrl = import.meta.env.VITE_API_URL;

  async login(credentials: LoginCredentials) {
    return this.request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
      skipAuth: true,
    });
  }

  async request<TResponse>(path: string, options: RequestInit & { skipAuth?: boolean } = {}) {
    const { skipAuth, ...requestOptions } = options;
    const response = await fetch(this.url(path), {
      ...requestOptions,
      headers: this.headers({ ...requestOptions, skipAuth }),
    });

    if (response.status === 401) {
      authToken.clear();
      this.redirectToLogin();
      throw new ApiError("Unauthorized", "UNAUTHORIZED", response.status);
    }

    if (!response.ok) {
      throw new ApiError("Request failed", "API_ERROR", response.status);
    }

    return (await response.json()) as TResponse;
  }

  private headers(options: RequestInit & { skipAuth?: boolean }) {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (options.headers) {
      new Headers(options.headers).forEach((value, key) => {
        headers[key] = value;
      });
    }

    if (!options.skipAuth) {
      const token = authToken.get();

      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
    }

    return headers;
  }

  private url(path: string) {
    return `${this.baseUrl}${path}`;
  }

  private redirectToLogin() {
    if (window.location.pathname !== "/login") {
      window.history.pushState({}, "", "/login");
      window.dispatchEvent(new PopStateEvent("popstate"));
    }
  }
}

export const apiClient = new ApiClient();
