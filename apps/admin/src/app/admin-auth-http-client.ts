import { frontendEnvConfig } from "@portfolio/shared-config";
import type { AdminLoginRequest, AdminSessionResponse } from "@portfolio/shared-contracts";

export const ADMIN_AUTH_EXPIRED_EVENT = "portfolio-admin-auth-expired";

let currentAdminCsrfToken: string | null = null;

export class AdminUnauthorizedError extends Error {
  public constructor(message = "Administrative session is missing or expired.") {
    super(message);
    this.name = "AdminUnauthorizedError";
  }
}

export function setAdminCsrfToken(nextCsrfToken: string | null): void {
  currentAdminCsrfToken = nextCsrfToken;
}

export async function requestAdminJson<TResponse>(
  pathname: string,
  init: RequestInit,
  signal?: AbortSignal,
): Promise<TResponse> {
  const headers = new Headers(init.headers ?? {});
  headers.set("Accept", "application/json");

  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (
    currentAdminCsrfToken &&
    init.method &&
    !["GET", "HEAD", "OPTIONS"].includes(init.method.toUpperCase())
  ) {
    headers.set("X-CSRF-Token", currentAdminCsrfToken);
  }

  const response = await fetch(pathname, {
    ...init,
    credentials: "include",
    headers,
    signal,
  });

  if (response.status === 401) {
    currentAdminCsrfToken = null;
    window.dispatchEvent(new CustomEvent(ADMIN_AUTH_EXPIRED_EVENT));
    throw new AdminUnauthorizedError();
  }

  if (!response.ok) {
    throw new Error(`Failed to fetch ${pathname}: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}

export async function fetchCurrentAdminSession(signal?: AbortSignal): Promise<AdminSessionResponse> {
  const sessionResponse = await requestAdminJson<AdminSessionResponse>(
    `${frontendEnvConfig.adminApiBaseUrl}/auth/session`,
    { method: "GET" },
    signal,
  );
  currentAdminCsrfToken = sessionResponse.csrfToken;
  return sessionResponse;
}

export async function loginToAdminPanel(
  requestPayload: AdminLoginRequest,
): Promise<AdminSessionResponse> {
  const sessionResponse = await requestAdminJson<AdminSessionResponse>(
    `${frontendEnvConfig.adminApiBaseUrl}/auth/session`,
    {
      method: "POST",
      body: JSON.stringify(requestPayload),
    },
  );
  currentAdminCsrfToken = sessionResponse.csrfToken;
  return sessionResponse;
}

export async function logoutFromAdminPanel(): Promise<void> {
  await requestAdminJson<void>(`${frontendEnvConfig.adminApiBaseUrl}/auth/session`, {
    method: "DELETE",
  });
  currentAdminCsrfToken = null;
}
