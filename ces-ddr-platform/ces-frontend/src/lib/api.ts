import { authToken } from "@/lib/auth";

export type LoginCredentials = {
  username: string;
  password: string;
};

export type LoginResponse = {
  token: string;
  expires_at: number;
};

export type DDRStatus = "queued" | "processing" | "complete" | "failed";

export type DDRDateStatus = "queued" | "success" | "warning" | "failed";

export type DDRDateDetail = {
  id: string;
  ddr_id: string;
  date: string;
  status: DDRDateStatus;
  raw_response?: Record<string, unknown> | null;
  final_json?: Record<string, unknown> | null;
  error_log?: Record<string, unknown> | null;
  created_at: number;
  updated_at: number;
};

export type DDRDetail = {
  id: string;
  file_path: string;
  status: DDRStatus;
  well_name?: string | null;
  created_at: number;
  dates?: DDRDateDetail[];
};

export type DDRUploadResponse = {
  id: string;
  status: DDRStatus;
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

  async getDDR(id: string) {
    return this.request<DDRDetail>(`/ddrs/${encodeURIComponent(id)}`);
  }

  async listDDRs() {
    return this.request<DDRDetail[]>("/ddrs");
  }

  ddrStatusStreamUrl(id: string) {
    const token = authToken.get();
    const url = new URL(this.url(`/ddrs/${encodeURIComponent(id)}/status/stream`));
    if (token) {
      url.searchParams.set("access_token", token);
    }
    return url.toString();
  }

  async uploadDDR(file: File, onProgress?: (progress: number) => void) {
    return new Promise<DDRUploadResponse>((resolve, reject) => {
      const request = new XMLHttpRequest();
      request.open("POST", this.url("/ddrs/upload"));
      const token = authToken.get();
      if (token) {
        request.setRequestHeader("Authorization", `Bearer ${token}`);
      }
      request.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      };
      request.onload = () => {
        if (request.status === 401) {
          authToken.clear();
          this.redirectToLogin();
          reject(new ApiError("Unauthorized", "UNAUTHORIZED", request.status));
          return;
        }
        if (request.status < 200 || request.status >= 300) {
          reject(new ApiError("Request failed", "API_ERROR", request.status));
          return;
        }
        resolve(JSON.parse(request.responseText) as DDRUploadResponse);
      };
      request.onerror = () => reject(new ApiError("Request failed", "API_ERROR", request.status || 0));
      const form = new FormData();
      form.append("file", file);
      request.send(form);
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

    if (response.status === 204) {
      return undefined as TResponse;
    }

    const body = await response.text();

    if (!body) {
      return undefined as TResponse;
    }

    return JSON.parse(body) as TResponse;
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
