interface ThemeSwitcherProps {
  currentThemeId: string;
  themes: Array<{ id: string; label: string }>;
  onThemeChange: (themeId: string) => void;
}

/**
 * Переключатель визуальной темы.
 */
export function ThemeSwitcher({
  currentThemeId,
  themes,
  onThemeChange,
}: ThemeSwitcherProps) {
  return (
    <label className="theme-switcher">
      <span className="theme-switcher__label">Theme</span>
      <select
        className="theme-switcher__select"
        value={currentThemeId}
        onChange={(event) => onThemeChange(event.target.value)}
      >
        {themes.map((themeOption) => (
          <option key={themeOption.id} value={themeOption.id}>
            {themeOption.label}
          </option>
        ))}
      </select>
    </label>
  );
}
