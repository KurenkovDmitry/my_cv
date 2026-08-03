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
  return (
    <div className="locale-switcher" role="group" aria-label="Language switcher">
      {availableLocales.map((localeOption) => {
        const isActive = localeOption.code === currentLocale;

        return (
          <button
            key={localeOption.code}
            className={`locale-switcher__button${isActive ? " locale-switcher__button--active" : ""}`}
            type="button"
            onClick={() => onLocaleChange(localeOption.code)}
            aria-pressed={isActive}
          >
            {localeOption.label}
          </button>
        );
      })}
    </div>
  );
}
