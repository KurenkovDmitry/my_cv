import { useEffect, useRef } from "react";
import type { RegionalLocaleCode } from "@portfolio/modules/localization";

export type ColorPreference = "system" | "light" | "dark";

export interface VisualPreferences {
  colorPreference: ColorPreference;
  ambientLight: boolean;
  pointerEdges: boolean;
  scrollUnroll: boolean;
}

interface SettingsPanelProps {
  open: boolean;
  localeCode: RegionalLocaleCode;
  themeId: string;
  preferences: VisualPreferences;
  onClose: () => void;
  onThemeChange: (themeId: string) => void;
  onPreferencesChange: (preferences: VisualPreferences) => void;
}

const themeOptions = [
  { id: "engineering-blueprint", labelRu: "Профессиональный IT", labelEn: "Professional IT" },
  { id: "papyrus-scroll", labelRu: "Древний папирус", labelEn: "Ancient papyrus" },
] as const;

/** Панель визуальных настроек. Эффекты выключаются независимо друг от друга. */
export function SettingsPanel({
  open,
  localeCode,
  themeId,
  preferences,
  onClose,
  onThemeChange,
  onPreferencesChange,
}: SettingsPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const isRussian = localeCode === "ru";

  useEffect(() => {
    if (!open) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    panelRef.current?.focus();
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, open]);

  if (!open) {
    return null;
  }

  const updatePreference = <Key extends keyof VisualPreferences>(
    key: Key,
    value: VisualPreferences[Key],
  ) => onPreferencesChange({ ...preferences, [key]: value });

  return (
    <div className="settings-drawer" role="presentation" onMouseDown={onClose}>
      <div
        ref={panelRef}
        className="settings-drawer__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        tabIndex={-1}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="settings-drawer__header">
          <div>
            <p className="settings-drawer__eyebrow">Interface / 01</p>
            <h2 id="settings-title" className="settings-drawer__title">
              {isRussian ? "Внешний вид" : "Appearance"}
            </h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label={isRussian ? "Закрыть" : "Close"}>
            <span aria-hidden="true">×</span>
          </button>
        </header>

        <fieldset className="settings-group">
          <legend>{isRussian ? "Стиль" : "Style"}</legend>
          <div className="theme-cards">
            {themeOptions.map((themeOption) => (
              <label
                className={`theme-card${themeId === themeOption.id ? " theme-card--active" : ""}`}
                key={themeOption.id}
              >
                <input
                  type="radio"
                  name="visual-theme"
                  value={themeOption.id}
                  checked={themeId === themeOption.id}
                  onChange={() => onThemeChange(themeOption.id)}
                />
                <span className={`theme-card__preview theme-card__preview--${themeOption.id}`} aria-hidden="true" />
                <span className="theme-card__label">
                  {isRussian ? themeOption.labelRu : themeOption.labelEn}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="settings-group">
          <legend>{isRussian ? "Цвет" : "Colour"}</legend>
          <div className="segmented-control">
            {(["system", "light", "dark"] as const).map((colorOption) => {
              const labels = isRussian
                ? { system: "Система", light: "Светлая", dark: "Тёмная" }
                : { system: "System", light: "Light", dark: "Dark" };

              return (
                <label key={colorOption}>
                  <input
                    type="radio"
                    name="color-mode"
                    checked={preferences.colorPreference === colorOption}
                    onChange={() => updatePreference("colorPreference", colorOption)}
                  />
                  <span>{labels[colorOption]}</span>
                </label>
              );
            })}
          </div>
        </fieldset>

        <fieldset className="settings-group settings-group--toggles">
          <legend>{isRussian ? "Эффекты" : "Effects"}</legend>
          <PreferenceToggle
            checked={preferences.ambientLight}
            title={isRussian ? "Живой свет" : "Ambient light"}
            description={isRussian ? "Медленное движение света по материалу. По умолчанию выключено." : "A slow light pass across the material. Off by default."}
            onChange={(checked) => updatePreference("ambientLight", checked)}
          />
          <PreferenceToggle
            checked={preferences.pointerEdges}
            title={isRussian ? "Края за курсором" : "Pointer-responsive edges"}
            description={isRussian ? "Двигаются только поля и кромка листа — текст остаётся стабильным." : "Only the margins and paper edge react; text remains stable."}
            onChange={(checked) => updatePreference("pointerEdges", checked)}
          />
          <PreferenceToggle
            checked={preferences.scrollUnroll}
            title={isRussian ? "Разворачивание при прокрутке" : "Scroll unrolling"}
            description={isRussian ? "В папирусной теме кромки работают как в раскрывающемся свитке." : "Papyrus edges behave like an opening scroll as you move down the page."}
            onChange={(checked) => updatePreference("scrollUnroll", checked)}
          />
        </fieldset>

        <p className="settings-drawer__note">
          {isRussian
            ? "При системном ограничении анимации все декоративные движения автоматически отключаются."
            : "All decorative motion is disabled automatically when the system requests reduced motion."}
        </p>
      </div>
    </div>
  );
}

interface PreferenceToggleProps {
  checked: boolean;
  title: string;
  description: string;
  onChange: (checked: boolean) => void;
}

function PreferenceToggle({ checked, title, description, onChange }: PreferenceToggleProps) {
  return (
    <label className="preference-toggle">
      <span className="preference-toggle__copy">
        <strong>{title}</strong>
        <span>{description}</span>
      </span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span className="preference-toggle__control" aria-hidden="true" />
    </label>
  );
}
