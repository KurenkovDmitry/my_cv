import type { RegionalLocaleCode } from "../types/locale";

const LOCALE_STORAGE_KEY = "portfolio.locale";

/**
 * Фасад хранения выбранной локали в браузере.
 */
export class LocaleStorageFacade {
  public readPreferredLocale(): RegionalLocaleCode | null {
    if (typeof window === "undefined") {
      return null;
    }

    const rawValue = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    if (rawValue === "ru" || rawValue === "en-GB" || rawValue === "en-US") {
      return rawValue;
    }

    // Мягкая миграция значения, сохранённого предыдущей версией витрины.
    return rawValue === "en" ? "en-GB" : null;
  }

  public persistPreferredLocale(localeCode: RegionalLocaleCode): void {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(LOCALE_STORAGE_KEY, localeCode);
  }
}
