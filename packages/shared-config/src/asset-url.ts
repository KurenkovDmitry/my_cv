import { frontendEnvConfig } from "./env";

/**
 * Строит URL управляемого файла относительно публичного API текущего сервера.
 *
 * В snapshot хранится только стабильный asset id, поэтому backup можно перенести
 * на другой домен без ручной замены абсолютных ссылок.
 */
export function resolveContentAssetUrl(assetId: string | undefined, fallbackUrl: string): string {
  if (!assetId) {
    return fallbackUrl;
  }

  return `${frontendEnvConfig.publicApiBaseUrl}/portfolio/assets/${encodeURIComponent(assetId)}`;
}
