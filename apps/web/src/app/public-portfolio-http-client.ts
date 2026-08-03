import { frontendEnvConfig } from "@portfolio/shared-config";
import type { PublicPortfolioResponse } from "@portfolio/shared-contracts";

/**
 * Загружает единый опубликованный snapshot портфолио.
 */
export async function fetchPublicPortfolio(signal?: AbortSignal): Promise<PublicPortfolioResponse> {
  const response = await fetch(`${frontendEnvConfig.publicApiBaseUrl}/portfolio`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch public portfolio: ${response.status}`);
  }

  return (await response.json()) as PublicPortfolioResponse;
}
