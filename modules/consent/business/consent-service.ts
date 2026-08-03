import type { AnalyticsConsentContent, ConsentStateSnapshot } from "@portfolio/shared-types";

/**
 * Вычисляет, нужно ли показывать согласие и разрешён ли доступ к сайту.
 */
export class ConsentService {
  shouldRequestConsent(
    consentContent: AnalyticsConsentContent,
    currentState: ConsentStateSnapshot | null,
  ): boolean {
    if (!currentState) {
      return true;
    }

    return currentState.version !== consentContent.version;
  }

  isAcceptedCurrentVersion(
    consentContent: AnalyticsConsentContent,
    currentState: ConsentStateSnapshot | null,
  ): boolean {
    return currentState?.state === "accepted" && currentState.version === consentContent.version;
  }

  isRejectedCurrentVersion(
    consentContent: AnalyticsConsentContent,
    currentState: ConsentStateSnapshot | null,
  ): boolean {
    return currentState?.state === "rejected" && currentState.version === consentContent.version;
  }
}
