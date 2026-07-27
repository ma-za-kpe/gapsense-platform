import { useEffect, useState } from "react";

import {
  applyThemePreference,
  readThemePreference,
  saveThemePreference,
  type ThemeMediaQuery,
  type ThemePreference,
  type ThemeStorage,
} from "../theme";

type ThemeSwitcherProps = {
  readonly mediaQuery?: ThemeMediaQuery;
  readonly root?: HTMLElement;
  readonly storage?: ThemeStorage;
  readonly themeColor?: HTMLMetaElement | null;
};

const themeOptions: readonly {
  readonly label: string;
  readonly shortLabel: string;
  readonly value: ThemePreference;
}[] = [
  { value: "light", label: "Light", shortLabel: "Light" },
  { value: "dark", label: "Dark", shortLabel: "Dark" },
  { value: "system", label: "System", shortLabel: "Auto" },
];

const createDefaultMediaQuery = (): ThemeMediaQuery => {
  if (typeof window.matchMedia !== "function") {
    return {
      matches: false,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    };
  }
  const query = window.matchMedia("(prefers-color-scheme: dark)");
  return {
    get matches() {
      return query.matches;
    },
    addEventListener: (_type, listener) => query.addEventListener("change", listener),
    removeEventListener: (_type, listener) => query.removeEventListener("change", listener),
  };
};

export function ThemeSwitcher({
  mediaQuery: suppliedMediaQuery,
  root = document.documentElement,
  storage = window.localStorage,
  themeColor = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]'),
}: ThemeSwitcherProps): React.JSX.Element {
  const [mediaQuery] = useState(() => suppliedMediaQuery ?? createDefaultMediaQuery());
  const [preference, setPreference] = useState(() => readThemePreference(storage));
  const [persistenceFailed, setPersistenceFailed] = useState(false);

  useEffect(() => {
    const syncTheme = () => {
      applyThemePreference(root, themeColor, preference, mediaQuery.matches);
    };
    syncTheme();
    if (preference !== "system") return undefined;
    mediaQuery.addEventListener("change", syncTheme);
    return () => mediaQuery.removeEventListener("change", syncTheme);
  }, [mediaQuery, preference, root, themeColor]);

  const chooseTheme = (nextPreference: ThemePreference): void => {
    setPreference(nextPreference);
    setPersistenceFailed(!saveThemePreference(storage, nextPreference));
  };

  return (
    <div className="theme-control">
      <fieldset className="theme-switcher">
        <legend className="visually-hidden">Theme</legend>
        {themeOptions.map((option) => (
          <label key={option.value}>
            <input
              type="radio"
              name="theme"
              value={option.value}
              checked={preference === option.value}
              onChange={() => chooseTheme(option.value)}
            />
            <span aria-label={option.label}>{option.shortLabel}</span>
          </label>
        ))}
      </fieldset>
      <select
        className="theme-select"
        aria-label="Theme"
        value={preference}
        onChange={(event) => chooseTheme(event.currentTarget.value as ThemePreference)}
      >
        {themeOptions.map((option) => (
          <option value={option.value} key={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {persistenceFailed ? (
        <span className="visually-hidden" role="status">
          Theme preference could not be saved on this device.
        </span>
      ) : null}
    </div>
  );
}
