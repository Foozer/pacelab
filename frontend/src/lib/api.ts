import type { HealthResponse } from "@/types/health";
import type {
  CsrfResponse,
  DevOutboxResponse,
  MessageResponse,
  UserPublic,
} from "@/types/auth";
import type {
  ActivityDetail,
  ActivityListQuery,
  ActivityListResponse,
  ActivitySyncResponse,
  DashboardResponse,
} from "@/types/activity";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  const found = document.cookie.split("; ").find((part) => part.startsWith(prefix));
  if (!found) {
    return null;
  }
  return decodeURIComponent(found.slice(prefix.length));
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const payload = (await response.json()) as { error?: { code?: string; message?: string } };
    return new ApiError(
      response.status,
      payload.error?.code ?? "HTTP_ERROR",
      payload.error?.message ?? `Request failed (${response.status})`,
    );
  } catch {
    return new ApiError(response.status, "HTTP_ERROR", `Request failed (${response.status})`);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (method !== "GET" && method !== "HEAD") {
    const csrf = readCookie("pacelab_csrf") ?? (await fetchCsrf());
    headers.set("X-CSRF-Token", csrf);
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    method,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    throw await parseError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function fetchCsrf(): Promise<string> {
  const response = await fetch(`${apiBaseUrl}/api/v1/auth/csrf`, {
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  const payload = (await response.json()) as CsrfResponse;
  return payload.csrf_token;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/health`, {
    headers: { Accept: "application/json" },
    credentials: "include",
  });
  if (!response.ok && response.status !== 503) {
    throw new Error(`Health check failed (${response.status})`);
  }
  return (await response.json()) as HealthResponse;
}

export async function fetchCurrentUser(): Promise<UserPublic | null> {
  try {
    return await request<UserPublic>("/api/v1/users/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

export function registerAccount(email: string, password: string): Promise<UserPublic> {
  return request<UserPublic>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string): Promise<UserPublic> {
  return request<UserPublic>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout(): Promise<MessageResponse> {
  return request<MessageResponse>("/api/v1/auth/logout", { method: "POST" });
}

export function verifyEmail(token: string): Promise<UserPublic> {
  return request<UserPublic>("/api/v1/auth/email/verify", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export function resendVerification(): Promise<MessageResponse> {
  return request<MessageResponse>("/api/v1/auth/email/resend", { method: "POST" });
}

export function requestPasswordReset(email: string): Promise<MessageResponse> {
  return request<MessageResponse>("/api/v1/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function confirmPasswordReset(token: string, password: string): Promise<MessageResponse> {
  return request<MessageResponse>("/api/v1/auth/password-reset/confirm", {
    method: "POST",
    body: JSON.stringify({ token, password }),
  });
}

export function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<UserPublic> {
  return request<UserPublic>("/api/v1/users/me/password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export function formatAuthError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong";
}

export async function fetchDevOutbox(): Promise<DevOutboxResponse | null> {
  try {
    return await request<DevOutboxResponse>("/api/v1/auth/dev/outbox");
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export function fetchActivities(query: ActivityListQuery): Promise<ActivityListResponse> {
  const params = new URLSearchParams({
    limit: String(query.limit),
    offset: String(query.offset),
  });
  if (query.fromDate) {
    params.set("from_date", query.fromDate);
  }
  if (query.toDate) {
    params.set("to_date", query.toDate);
  }
  if (query.activityType) {
    params.set("activity_type", query.activityType);
  }
  return request<ActivityListResponse>(`/api/v1/activities?${params.toString()}`);
}

export function fetchActivity(activityId: string): Promise<ActivityDetail> {
  return request<ActivityDetail>(`/api/v1/activities/${activityId}`);
}

export function fetchDashboard(): Promise<DashboardResponse> {
  return request<DashboardResponse>("/api/v1/dashboard");
}

export function syncActivities(): Promise<ActivitySyncResponse> {
  return request<ActivitySyncResponse>("/api/v1/activities/sync", { method: "POST" });
}
