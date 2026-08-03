import type { ThemeDefinition } from "@portfolio/shared-types";
import type { ThemeOption } from "../types/theme";

/**
 * Сервис темизации frontend.
 */
export class ThemeService {
  public constructor(
    private readonly availableThemes: ThemeDefinition[],
    private readonly defaultThemeId: string,
  ) {}

  public getThemeOptions(localeCode: "ru" | "en"): ThemeOption[] {
    return this.availableThemes.map((themeDefinition) => ({
      id: themeDefinition.id,
      label: themeDefinition.label[localeCode],
    }));
  }

  public resolveInitialTheme(storedThemeId?: string | null): string {
    if (storedThemeId && this.availableThemes.some((themeDefinition) => themeDefinition.id === storedThemeId)) {
      return storedThemeId;
    }

    return this.defaultThemeId;
  }

  public applyTheme(themeId: string): void {
    if (typeof document === "undefined") {
      return;
    }

    document.documentElement.dataset.theme = themeId;
  }
}

