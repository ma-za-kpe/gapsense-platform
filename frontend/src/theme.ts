export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = Exclude<ThemePreference, "system">;

export type ThemeStorage = {
  readonly getItem: (key: string) => string | null;
  readonly setItem: (key: string, value: string) => void;
};

export type ThemeMediaQuery = {
  readonly matches: boolean;
  readonly addEventListener: (type: "change", listener: () => void) => void;
  readonly removeEventListener: (type: "change", listener: () => void) => void;
};

export const themeStorageKey = "gapsense.theme-preference.v1";

const lightThemeColor = "#fbfcf8";
const darkThemeColor = "#102a27";

export const isThemePreference = (value: string | null): value is ThemePreference =>
  value === "light" || value === "dark" || value === "system";

export const readThemePreference = (storage: ThemeStorage): ThemePreference => {
  try {
    const value = storage.getItem(themeStorageKey);
    return isThemePreference(value) ? value : "system";
  } catch {
    return "system";
  }
};

export const saveThemePreference = (
  storage: ThemeStorage,
  preference: ThemePreference,
): boolean => {
  try {
    storage.setItem(themeStorageKey, preference);
    return true;
  } catch {
    return false;
  }
};

export const resolveTheme = (
  preference: ThemePreference,
  systemUsesDark: boolean,
): ResolvedTheme => {
  if (preference !== "system") return preference;
  return systemUsesDark ? "dark" : "light";
};

export const applyThemePreference = (
  root: HTMLElement,
  themeColor: HTMLMetaElement | null,
  preference: ThemePreference,
  systemUsesDark: boolean,
): ResolvedTheme => {
  const resolved = resolveTheme(preference, systemUsesDark);
  root.dataset.theme = resolved;
  root.dataset.themePreference = preference;
  root.style.colorScheme = resolved;
  if (themeColor !== null) {
    themeColor.content = resolved === "dark" ? darkThemeColor : lightThemeColor;
  }
  return resolved;
};
