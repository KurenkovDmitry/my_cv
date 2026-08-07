import type {
  AnalyticsSectionClickEventPayload,
  AnalyticsSectionViewEventPayload,
  AnalyticsStorageMode,
  AnalyticsSessionEventPayload,
  LocaleCode,
} from "@portfolio/shared-types";
import { AnalyticsEventFacade } from "../api/analytics-event-facade";

const SESSION_NONCE_STORAGE_KEY = "portfolio.analytics.session-nonce";
const DEDUPE_BUCKET_STORAGE_KEY = "portfolio.analytics.dedupe-bucket";

const SESSION_EVENT_TTL_MS = 12 * 60 * 60 * 1_000;
const SECTION_VIEW_TTL_MS = 15_000;
const SECTION_CLICK_TTL_MS = 5_000;
const MAX_DEDUPE_ITEMS = 120;

let memoryDedupeBucket: Record<string, number> = {};
let memorySessionNonce: string | null = null;

/**
 * Клиентская антидубль-логика для полностью обезличенной аналитики.
 *
 * Она не формирует постоянный browser id и не связывает события с пользователем.
 * Нужна только для того, чтобы не накручивать счетчики частыми перезагрузками и повторными кликами.
 */
export class AnalyticsService {
  private sessionNonce: string | null = null;
  private consentStorageMode: AnalyticsStorageMode = "memory_only";

  constructor(private readonly analyticsEventFacade: AnalyticsEventFacade) {}

  async bootstrapAcceptedSession(
    entryRouteKey: string,
    localeCode: LocaleCode,
    storageMode: AnalyticsStorageMode,
  ): Promise<void> {
    this.consentStorageMode = storageMode;
    this.sessionNonce = this.ensureSessionNonce();

    const sessionEvent: AnalyticsSessionEventPayload = {
      entryRouteKey,
      localeCode,
      consentState: "accepted",
      storageMode: this.consentStorageMode,
      sessionNonce: this.sessionNonce,
      occurredAt: new Date().toISOString(),
    };

    const sessionEventKey = "session";

    if (this.shouldSkipEvent(sessionEventKey, SESSION_EVENT_TTL_MS)) {
      return;
    }

    await this.analyticsEventFacade.sendSessionEvent({ event: sessionEvent });
  }

  async trackRouteSections(
    routeKey: string,
    localeCode: LocaleCode,
    sectionKeys: string[],
  ): Promise<void> {
    if (!this.sessionNonce) {
      return;
    }

    for (const sectionKey of sectionKeys) {
      const viewEvent: AnalyticsSectionViewEventPayload = {
        routeKey,
        sectionKey,
        localeCode,
        viewSource: "ssr_render",
        sessionNonce: this.sessionNonce,
        occurredAt: new Date().toISOString(),
      };

      const viewEventKey = `view:${routeKey}:${sectionKey}:${localeCode}`;

      if (this.shouldSkipEvent(viewEventKey, SECTION_VIEW_TTL_MS)) {
        continue;
      }

      await this.analyticsEventFacade.sendSectionViewEvent({ event: viewEvent });
    }
  }

  trackActionClick(
    routeKey: string,
    sectionKey: string,
    actionKey: string,
    localeCode: LocaleCode,
  ): void {
    if (!this.sessionNonce) {
      return;
    }

    const clickEventKey = `click:${routeKey}:${sectionKey}:${actionKey}:${localeCode}`;

    if (this.shouldSkipEvent(clickEventKey, SECTION_CLICK_TTL_MS)) {
      return;
    }

    const clickEvent: AnalyticsSectionClickEventPayload = {
      routeKey,
      sectionKey,
      actionKey,
      localeCode,
      sessionNonce: this.sessionNonce,
      occurredAt: new Date().toISOString(),
    };

    void this.analyticsEventFacade.sendSectionClickEvent({ event: clickEvent });
  }

  private ensureSessionNonce(): string {
    const sessionStorageRef = this.getStorage("sessionStorage");

    if (sessionStorageRef) {
      const existingNonce = sessionStorageRef.getItem(SESSION_NONCE_STORAGE_KEY);

      if (existingNonce) {
        return existingNonce;
      }

      const nextNonce = this.createNonce();
      sessionStorageRef.setItem(SESSION_NONCE_STORAGE_KEY, nextNonce);
      return nextNonce;
    }

    if (memorySessionNonce) {
      return memorySessionNonce;
    }

    memorySessionNonce = this.createNonce();
    return memorySessionNonce;
  }

  private shouldSkipEvent(eventKey: string, ttlMs: number): boolean {
    const nowTimestamp = Date.now();
    const dedupeBucket = this.readDedupeBucket();
    const lastSeenTimestamp = dedupeBucket[eventKey];

    if (typeof lastSeenTimestamp === "number" && nowTimestamp - lastSeenTimestamp < ttlMs) {
      return true;
    }

    dedupeBucket[eventKey] = nowTimestamp;
    const normalizedBucket = this.pruneBucket(dedupeBucket, nowTimestamp);
    this.writeDedupeBucket(normalizedBucket);
    return false;
  }

  private pruneBucket(
    dedupeBucket: Record<string, number>,
    nowTimestamp: number,
  ): Record<string, number> {
    const ttlBorder =
      nowTimestamp - Math.max(SESSION_EVENT_TTL_MS, SECTION_VIEW_TTL_MS, SECTION_CLICK_TTL_MS);
    const filteredEntries = Object.entries(dedupeBucket)
      .filter(([, storedTimestamp]) => storedTimestamp >= ttlBorder)
      .sort((leftEntry, rightEntry) => rightEntry[1] - leftEntry[1])
      .slice(0, MAX_DEDUPE_ITEMS);

    return Object.fromEntries(filteredEntries);
  }

  private readDedupeBucket(): Record<string, number> {
    const localStorageRef = this.getStorage("localStorage");

    if (localStorageRef) {
      return this.deserializeBucket(localStorageRef.getItem(DEDUPE_BUCKET_STORAGE_KEY));
    }

    const sessionStorageRef = this.getStorage("sessionStorage");

    if (sessionStorageRef) {
      return this.deserializeBucket(sessionStorageRef.getItem(DEDUPE_BUCKET_STORAGE_KEY));
    }

    return memoryDedupeBucket;
  }

  private writeDedupeBucket(dedupeBucket: Record<string, number>): void {
    const localStorageRef = this.getStorage("localStorage");

    if (localStorageRef) {
      localStorageRef.setItem(DEDUPE_BUCKET_STORAGE_KEY, JSON.stringify(dedupeBucket));
      return;
    }

    const sessionStorageRef = this.getStorage("sessionStorage");

    if (sessionStorageRef) {
      sessionStorageRef.setItem(DEDUPE_BUCKET_STORAGE_KEY, JSON.stringify(dedupeBucket));
      return;
    }

    memoryDedupeBucket = dedupeBucket;
  }

  private deserializeBucket(rawBucket: string | null): Record<string, number> {
    if (!rawBucket) {
      return {};
    }

    try {
      return JSON.parse(rawBucket) as Record<string, number>;
    } catch {
      return {};
    }
  }

  private getStorage(storageKind: "localStorage" | "sessionStorage"): Storage | null {
    if (typeof window === "undefined") {
      return null;
    }

    try {
      return window[storageKind];
    } catch {
      return null;
    }
  }

  private createNonce(): string {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }

    return `anon-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
  }
}
