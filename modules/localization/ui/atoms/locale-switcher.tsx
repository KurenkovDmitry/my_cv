import type { LocaleCode } from "../../types/locale";

interface LocaleSwitcherProps {
  currentLocale: LocaleCode;
  availableLocales: Array<{ code: LocaleCode; label: string }>;
  onLocaleChange: (localeCode: LocaleCode) => void;
}

/**
 * Переключатель языка в шапке и административной панели.
 */
export function LocaleSwitcher({
  currentLocale,
  availableLocales,
  onLocaleChange,
}: LocaleSwitcherProps) {
  const switcherLabel = currentLocale === "ru" ? "Язык" : "Language";

  return (
    <label className="locale-switcher">
      <span className="locale-switcher__label">{switcherLabel}</span>
      <select
        className="locale-switcher__select"
        value={currentLocale}
        onChange={(event) => onLocaleChange(event.target.value as LocaleCode)}
        aria-label={switcherLabel}
      >
        {availableLocales.map((localeOption) => (
          <option key={localeOption.code} value={localeOption.code}>
            {localeOption.label}
          </option>
        ))}
      </select>
    </label>
  );
}
