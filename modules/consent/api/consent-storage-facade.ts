import type {
  AnalyticsStorageMode,
  ConsentDecision,
  ConsentStateSnapshot,
} from "@portfolio/shared-types";

const CONSENT_STORAGE_KEY = "portfolio.analytics-consent";

let memoryFallbackState: ConsentStateSnapshot | null = null;

/**
 * Хранит решение по согласию без привязки к личности пользователя.
 *
 * Приоритет хранения:
 * 1. localStorage
 * 2. sessionStorage
 * 3. memory-only fallback
 *
 * HttpOnly cookie здесь не пишется, потому что клиентский JS не должен создавать такой cookie.
 * Если backend захочет зеркалировать согласие в HttpOnly cookie, это делается сервером отдельно.
 */
export class ConsentStorageFacade {
  readConsentState(): ConsentStateSnapshot | null {
    const localStorageState = this.readFromStorage(this.getStorage("localStorage"));

    if (localStorageState) {
      return localStorageState;
    }

    const sessionStorageState = this.readFromStorage(this.getStorage("sessionStorage"));

    if (sessionStorageState) {
      return sessionStorageState;
    }

    return memoryFallbackState;
  }

  persistAccepted(version: string): ConsentStateSnapshot {
    return this.persistState("accepted", version);
  }

  persistRejected(version: string): ConsentStateSnapshot {
    return this.persistState("rejected", version);
  }

  private persistState(state: ConsentDecision, version: string): ConsentStateSnapshot {
    const resolvedStorage = this.resolveWritableStorage();
    const nextState: ConsentStateSnapshot = {
      version,
      state,
      storageMode: resolvedStorage.mode,
      updatedAt: new Date().toISOString(),
    };

    if (resolvedStorage.storage) {
      resolvedStorage.storage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(nextState));
    } else {
      memoryFallbackState = nextState;
    }

    return nextState;
  }

  private resolveWritableStorage(): {
    storage: Storage | null;
    mode: AnalyticsStorageMode;
  } {
    const localStorageRef = this.getStorage("localStorage");

    if (localStorageRef) {
      return { storage: localStorageRef, mode: "local_storage" };
    }

    const sessionStorageRef = this.getStorage("sessionStorage");

    if (sessionStorageRef) {
      return { storage: sessionStorageRef, mode: "session_storage" };
    }

    return { storage: null, mode: "memory_only" };
  }

  private readFromStorage(storageRef: Storage | null): ConsentStateSnapshot | null {
    if (!storageRef) {
      return null;
    }

    try {
      const rawValue = storageRef.getItem(CONSENT_STORAGE_KEY);

      if (!rawValue) {
        return null;
      }

      return JSON.parse(rawValue) as ConsentStateSnapshot;
    } catch {
      return null;
    }
  }

  private getStorage(storageKind: "localStorage" | "sessionStorage"): Storage | null {
    if (typeof window === "undefined") {
      return null;
    }

    try {
      const storageRef = window[storageKind];
      const probeKey = `${CONSENT_STORAGE_KEY}.probe`;
      storageRef.setItem(probeKey, "1");
      storageRef.removeItem(probeKey);
      return storageRef;
    } catch {
      return null;
    }
  }
}
