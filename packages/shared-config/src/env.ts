/**
 * Публичная конфигурация frontend.
 *
 * Все значения безопасны для отдачи в браузер и не содержат секретов.
 */
export interface FrontendEnvConfig {
  publicApiBaseUrl: string;
  adminApiBaseUrl: string;
  enableDynamicBackdrop: boolean;
}

export const frontendEnvConfig: FrontendEnvConfig = {
  publicApiBaseUrl: import.meta.env.VITE_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/public",
  adminApiBaseUrl: import.meta.env.VITE_ADMIN_API_BASE_URL ?? "http://localhost:8000/api/admin",
  enableDynamicBackdrop: (import.meta.env.VITE_ENABLE_DYNAMIC_BACKDROP ?? "true") === "true"
};

