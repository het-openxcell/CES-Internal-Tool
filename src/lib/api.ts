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

export type OccurrenceRow = {
  id: string;
  ddr_id: string;
  well_name: string | null;
  surface_location: string | null;
  type: string;
  section: string | null;
  mmd: number | null;
  density: number | null;
  notes: string | null;
  date: string | null;
  page_number: number | null;
};

export type OccurrenceFilters = {
  type?: string;
  section?: string;
  date_from?: string;
  date_to?: string;
};

export type OccurrenceEditResponse = {
  id: string;
  occurrence_id: string;
  ddr_id: string;
  field: string;
  original_value: string | null;
  corrected_value: string | null;
  reason: string | null;
  created_by: string | null;
  created_at: number;
};

export type MonitorMetrics = {
  ddrs_this_week: number;
  occurrences_extracted: number;
  ai_cost_weekly: number;
  failed_dates: number;
  corrections_this_week: number;
  avg_processing_seconds: number;
  exports_this_week: number;
  uptime_month: number;
};

export type QueueItem = {
  id: string;
  file_path: string;
  well_name: string | null;
  operator: string | null;
  area: string | null;
  status: DDRStatus;
  date_total: number;
  date_success: number;
  date_failed: number;
  date_warning: number;
  created_at: number;
  updated_at: number;
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

  async uploadDDR(file: File, operator?: string, area?: string, onProgress?: (progress: number) => void) {
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
      if (operator) form.append("operator", operator);
      if (area) form.append("area", area);
      request.send(form);
    });
  }

  async retryDate(ddrId: string, date: string) {
    return this.request<DDRDateDetail>(`/ddrs/${encodeURIComponent(ddrId)}/dates/${encodeURIComponent(date)}/retry`, {
      method: "POST",
    });
  }

  async reprocessFull(ddrId: string) {
    return this.request<{ status: string; mode: string }>(
      `/ddrs/${encodeURIComponent(ddrId)}/reprocess/full`,
      { method: "POST", body: JSON.stringify({}) },
    );
  }

  async reprocessDates(ddrId: string, dates: string[] | "all") {
    return this.request<{ status: string; mode: string; dates: string[] | null }>(
      `/ddrs/${encodeURIComponent(ddrId)}/reprocess/dates`,
      { method: "POST", body: JSON.stringify({ dates }) },
    );
  }

  async reprocessOccurrences(ddrId: string) {
    return this.request<{ status: string; mode: string; total_occurrences?: number; error?: string }>(
      `/ddrs/${encodeURIComponent(ddrId)}/reprocess/occurrences`,
      { method: "POST", body: JSON.stringify({}) },
    );
  }

  async getOccurrences(ddrId: string, filters?: OccurrenceFilters, signal?: AbortSignal) {
    const params = new URLSearchParams();
    if (filters?.type) params.set("type", filters.type);
    if (filters?.section) params.set("section", filters.section);
    if (filters?.date_from) params.set("date_from", filters.date_from);
    if (filters?.date_to) params.set("date_to", filters.date_to);
    const query = params.toString() ? `?${params.toString()}` : "";
    return this.request<OccurrenceRow[]>(`/ddrs/${encodeURIComponent(ddrId)}/occurrences${query}`, { signal });
  }

  async patchOccurrence(ddrId: string, occurrenceId: string, field: string, value: string | null, reason?: string) {
    return this.request<OccurrenceEditResponse>(
      `/ddrs/${encodeURIComponent(ddrId)}/occurrences/${encodeURIComponent(occurrenceId)}`,
      { method: "PATCH", body: JSON.stringify({ field, value, reason }) },
    );
  }

  async getMonitorMetrics() {
    return this.request<MonitorMetrics>("/monitor/metrics");
  }

  async getMonitorQueue() {
    return this.request<QueueItem[]>("/monitor/queue");
  }

  async getMonitorCorrections(field?: string) {
    const params = field ? `?field=${encodeURIComponent(field)}` : "";
    return this.request<OccurrenceEditResponse[]>(`/monitor/corrections${params}`);
  }

  async getKeywords() {
    return this.request<Record<string, string>>("/keywords");
  }

  async updateKeywords(keywords: Record<string, string>) {
    return this.request<{ updated: number }>("/keywords", {
      method: "PUT",
      body: JSON.stringify(keywords),
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
      throw new ApiError("Unexpected empty response body", "API_ERROR", response.status);
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
      window.location.href = "/login";
    }
  }
}

export const apiClient = new ApiClient();
