import type { LocaleCode, LocaleOption, LocalizedText } from "../types/locale";

/**
 * Сервис локализации frontend.
 *
 * Содержит только безопасную клиентскую логику: выбор активной локали,
 * работу с автоопределением и получение строки из локализованного объекта.
 */
export class LocaleService {
  public constructor(
    private readonly supportedLocales: LocaleCode[],
    private readonly defaultLocale: LocaleCode,
    private readonly regionMap: Record<string, LocaleCode>,
  ) {}

  public resolveInitialLocale(browserLanguage?: string, regionCode?: string): LocaleCode {
    if (regionCode && this.regionMap[regionCode]) {
      return this.regionMap[regionCode];
    }

    if (browserLanguage?.toLowerCase().startsWith("ru")) {
      return "ru";
    }

    return this.defaultLocale;
  }

  public getLocaleOptions(): LocaleOption[] {
    return this.supportedLocales.map((localeCode) => ({
      code: localeCode,
      label: localeCode === "ru" ? "RU" : "EN",
    }));
  }

  public translate(localizedText: LocalizedText, localeCode: LocaleCode): string {
    return localizedText[localeCode] || localizedText[this.defaultLocale];
  }
}

