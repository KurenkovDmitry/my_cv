import type { LocaleCode } from "../types/locale";

const LOCALE_STORAGE_KEY = "portfolio.locale";

/**
 * Фасад хранения выбранной локали в браузере.
 */
export class LocaleStorageFacade {
  public readPreferredLocale(): LocaleCode | null {
    if (typeof window === "undefined") {
      return null;
    }

    const rawValue = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    return rawValue === "ru" || rawValue === "en" ? rawValue : null;
  }

  public persistPreferredLocale(localeCode: LocaleCode): void {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(LOCALE_STORAGE_KEY, localeCode);
  }
}

