import { describe, expect, it, vi } from "vitest";

import {
  applyThemePreference,
  isThemePreference,
  readThemePreference,
  resolveTheme,
  saveThemePreference,
  themeStorageKey,
} from "./theme";

describe("theme preference", () => {
  it.each(["light", "dark", "system"] as const)("accepts the %s preference", (preference) => {
    expect(isThemePreference(preference)).toBe(true);
    expect(readThemePreference({ getItem: () => preference, setItem: vi.fn() })).toBe(preference);
  });

  it.each([null, "", "sepia"])("falls back safely for the stored value %s", (stored) => {
    expect(isThemePreference(stored)).toBe(false);
    expect(readThemePreference({ getItem: () => stored, setItem: vi.fn() })).toBe("system");
  });

  it("falls back to system when storage cannot be read", () => {
    expect(
      readThemePreference({
        getItem: () => {
          throw new DOMException("blocked");
        },
        setItem: vi.fn(),
      }),
    ).toBe("system");
  });

  it("persists only the allowlisted preference key", () => {
    const setItem = vi.fn();
    expect(saveThemePreference({ getItem: vi.fn(), setItem }, "dark")).toBe(true);
    expect(setItem).toHaveBeenCalledWith(themeStorageKey, "dark");
  });

  it("reports unavailable preference storage without throwing", () => {
    expect(
      saveThemePreference(
        {
          getItem: vi.fn(),
          setItem: () => {
            throw new DOMException("blocked");
          },
        },
        "light",
      ),
    ).toBe(false);
  });

  it.each([
    ["light", false, "light"],
    ["light", true, "light"],
    ["dark", false, "dark"],
    ["dark", true, "dark"],
    ["system", false, "light"],
    ["system", true, "dark"],
  ] as const)("resolves %s with system-dark=%s to %s", (preference, systemDark, expected) => {
    expect(resolveTheme(preference, systemDark)).toBe(expected);
  });

  it("applies the resolved theme before rendering and updates browser chrome", () => {
    const root = document.createElement("html");
    const themeColor = document.createElement("meta");

    expect(applyThemePreference(root, themeColor, "system", true)).toBe("dark");
    expect(root).toHaveAttribute("data-theme", "dark");
    expect(root).toHaveAttribute("data-theme-preference", "system");
    expect(root.style.colorScheme).toBe("dark");
    expect(themeColor).toHaveAttribute("content", "#102a27");

    expect(applyThemePreference(root, themeColor, "light", true)).toBe("light");
    expect(root).toHaveAttribute("data-theme", "light");
    expect(root.style.colorScheme).toBe("light");
    expect(themeColor).toHaveAttribute("content", "#fbfcf8");

    expect(applyThemePreference(root, null, "dark", false)).toBe("dark");
  });
});
