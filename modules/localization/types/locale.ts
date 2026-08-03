import type { LocaleCode, LocalizedText } from "@portfolio/shared-types";

export interface LocaleOption {
  code: LocaleCode;
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

