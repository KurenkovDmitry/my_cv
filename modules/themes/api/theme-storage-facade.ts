const THEME_STORAGE_KEY = "portfolio.theme";

/**
 * Фасад хранения темы в браузере.
 */
export class ThemeStorageFacade {
  public readPreferredTheme(): string | null {
    if (typeof window === "undefined") {
      return null;
    }

    return window.localStorage.getItem(THEME_STORAGE_KEY);
  }

  public persistPreferredTheme(themeId: string): void {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(THEME_STORAGE_KEY, themeId);
  }
}

