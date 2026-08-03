import type {
  AnalyticsSectionClickIngestRequest,
  AnalyticsSectionViewIngestRequest,
  AnalyticsSessionIngestRequest,
} from "@portfolio/shared-contracts";

/**
 * Отправляет анонимные агрегируемые события в публичный backend-контур.
 */
export class AnalyticsEventFacade {
  constructor(private readonly apiBaseUrl: string) {}

  async sendSessionEvent(request: AnalyticsSessionIngestRequest): Promise<void> {
    await this.postEvent("/analytics/events/session", request);
  }

  async sendSectionViewEvent(request: AnalyticsSectionViewIngestRequest): Promise<void> {
    await this.postEvent("/analytics/events/section-view", request);
  }

  async sendSectionClickEvent(request: AnalyticsSectionClickIngestRequest): Promise<void> {
    await this.postEvent("/analytics/events/section-click", request);
  }

  private async postEvent(pathname: string, payload: object): Promise<void> {
    const endpointUrl = `${this.apiBaseUrl}${pathname}`;
    const requestBody = JSON.stringify(payload);

    if (typeof navigator !== "undefined" && "sendBeacon" in navigator) {
      try {
        const beaconBody = new Blob([requestBody], { type: "application/json" });

        if (navigator.sendBeacon(endpointUrl, beaconBody)) {
          return;
        }
      } catch {
        // Если sendBeacon не сработал, ниже есть fetch-fallback.
      }
    }

    try {
      await fetch(endpointUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: requestBody,
        keepalive: true,
      });
    } catch {
      // Ошибка доставки аналитики не должна ломать пользовательский сценарий.
    }
  }
}
