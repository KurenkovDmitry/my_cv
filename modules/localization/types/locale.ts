import type { LocaleCode, LocalizedText } from "@portfolio/shared-types";

export interface LocaleOption {
  code: LocaleCode;
  label: string;
}

/** Региональный вариант витрины: перевод общий, а композиция и тон адаптируются под рынок. */
export type RegionalLocaleCode = "ru" | "en-GB" | "en-US";

export interface RegionalLocaleOption {
  code: RegionalLocaleCode;
  label: string;
}

/**
 * Представление перевода, готовое для UI.
 */
export interface LocalizedValueViewModel {
  locale: LocaleCode;
  value: string;
}

export type { LocaleCode, LocalizedText };
