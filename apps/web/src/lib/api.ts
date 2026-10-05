/**
 * Mail Agent API Client
 * Provides typed HTTP methods calling same-origin `/api/v1` endpoints (proxied by Next.js).
 * Includes credentials (cookies) and CSRF protection headers for mutating requests.
 */

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    public readonly detail: string,
    public readonly raw?: unknown,
  ) {
    super(detail || `API request failed with status ${status}`);
    this.name = "ApiError";
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined | null>;
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { params, headers, ...rest } = options;

  let url = path.startsWith("/") ? path : `/${path}`;
  if (!url.startsWith("/api/")) {
    url = `/api/v1${url}`;
  }

  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    }
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  const defaultHeaders: Record<string, string> = {
    Accept: "application/json",
  };

  const isMutation = ["POST", "PUT", "PATCH", "DELETE"].includes(
    (options.method || "GET").toUpperCase(),
  );

  if (isMutation) {
    defaultHeaders["X-Requested-With"] = "XMLHttpRequest";
    defaultHeaders["X-CSRF-Token"] = "mailagent-csrf";
  }

  if (options.body && typeof options.body === "string") {
    defaultHeaders["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    ...rest,
    credentials: "same-origin",
    headers: {
      ...defaultHeaders,
      ...(headers as Record<string, string>),
    },
  });

  if (!response.ok) {
    let errorCode = "UNKNOWN_ERROR";
    let detail = `Request failed with status ${response.status}`;
    let rawBody: unknown;

    try {
      rawBody = await response.json();
      if (typeof rawBody === "object" && rawBody !== null) {
        const bodyRecord = rawBody as Record<string, unknown>;
        if (typeof bodyRecord["code"] === "string") {
          errorCode = bodyRecord["code"];
        }
        if (typeof bodyRecord["detail"] === "string") {
          detail = bodyRecord["detail"];
        } else if (typeof bodyRecord["title"] === "string") {
          detail = bodyRecord["title"];
        }
      }
    } catch {
      // Body was not JSON
    }

    throw new ApiError(response.status, errorCode, detail, rawBody);
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(
    url: string,
    params?: Record<string, string | number | boolean | undefined | null>,
  ) => request<T>(url, { method: "GET", params }),

  post: <T>(url: string, body?: unknown) =>
    request<T>(url, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  patch: <T>(url: string, body?: unknown) =>
    request<T>(url, {
      method: "PATCH",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(url: string) => request<T>(url, { method: "DELETE" }),
};
