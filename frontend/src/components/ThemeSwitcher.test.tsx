import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ThemeSwitcher } from "./ThemeSwitcher";
import { themeStorageKey, type ThemeMediaQuery } from "../theme";

type MutableMediaQuery = ThemeMediaQuery & {
  readonly listenerCount: () => number;
  readonly setDark: (matches: boolean) => void;
};

const createMediaQuery = (initiallyDark: boolean): MutableMediaQuery => {
  let matches = initiallyDark;
  const listeners = new Set<() => void>();
  return {
    get matches() {
      return matches;
    },
    addEventListener: (_type, listener) => listeners.add(listener),
    removeEventListener: (_type, listener) => listeners.delete(listener),
    listenerCount: () => listeners.size,
    setDark: (next) => {
      matches = next;
      listeners.forEach((listener) => listener());
    },
  };
};

describe("appearance switcher", () => {
  it("applies a stored explicit preference without waiting for system changes", () => {
    const mediaQuery = createMediaQuery(false);
    const root = document.createElement("html");
    const themeColor = document.createElement("meta");

    render(
      <ThemeSwitcher
        mediaQuery={mediaQuery}
        root={root}
        storage={{ getItem: () => "dark", setItem: vi.fn() }}
        themeColor={themeColor}
      />,
    );

    expect(screen.getByRole("radio", { name: "Dark" })).toBeChecked();
    expect(root).toHaveAttribute("data-theme", "dark");
    expect(mediaQuery.listenerCount()).toBe(0);
  });

  it("tracks operating-system changes while system mode is selected", () => {
    const mediaQuery = createMediaQuery(false);
    const root = document.createElement("html");
    const view = render(
      <ThemeSwitcher
        mediaQuery={mediaQuery}
        root={root}
        storage={{ getItem: () => null, setItem: vi.fn() }}
        themeColor={null}
      />,
    );

    expect(screen.getByRole("radio", { name: "System" })).toBeChecked();
    expect(root).toHaveAttribute("data-theme", "light");
    expect(mediaQuery.listenerCount()).toBe(1);

    act(() => mediaQuery.setDark(true));
    expect(root).toHaveAttribute("data-theme", "dark");
    view.unmount();
    expect(mediaQuery.listenerCount()).toBe(0);
  });

  it("lets the user choose all three modes and stores no other data", async () => {
    const user = userEvent.setup();
    const setItem = vi.fn();
    const root = document.createElement("html");
    const mediaQuery = createMediaQuery(true);
    render(
      <ThemeSwitcher
        mediaQuery={mediaQuery}
        root={root}
        storage={{ getItem: () => null, setItem }}
        themeColor={null}
      />,
    );

    await user.click(screen.getByRole("radio", { name: "Light" }));
    expect(root).toHaveAttribute("data-theme", "light");
    await user.click(screen.getByRole("radio", { name: "Dark" }));
    expect(root).toHaveAttribute("data-theme", "dark");
    await user.click(screen.getByRole("radio", { name: "System" }));
    expect(root).toHaveAttribute("data-theme", "dark");
    expect(setItem.mock.calls).toEqual([
      [themeStorageKey, "light"],
      [themeStorageKey, "dark"],
      [themeStorageKey, "system"],
    ]);
  });

  it("offers the same explicit choices through the compact mobile control", async () => {
    const user = userEvent.setup();
    const setItem = vi.fn();
    const root = document.createElement("html");
    render(
      <ThemeSwitcher
        mediaQuery={createMediaQuery(false)}
        root={root}
        storage={{ getItem: () => "system", setItem }}
        themeColor={null}
      />,
    );

    const select = screen.getByRole("combobox", { name: "Theme" });
    expect(select).toHaveValue("system");
    await user.selectOptions(select, "dark");

    expect(root).toHaveAttribute("data-theme", "dark");
    expect(setItem).toHaveBeenLastCalledWith(themeStorageKey, "dark");
  });

  it("keeps the selected mode usable when storage is unavailable", async () => {
    const user = userEvent.setup();
    const root = document.createElement("html");
    render(
      <ThemeSwitcher
        mediaQuery={createMediaQuery(false)}
        root={root}
        storage={{
          getItem: () => null,
          setItem: () => {
            throw new DOMException("blocked");
          },
        }}
        themeColor={null}
      />,
    );

    await user.click(screen.getByRole("radio", { name: "Dark" }));
    expect(root).toHaveAttribute("data-theme", "dark");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Theme preference could not be saved on this device.",
    );
  });

  it("adapts the browser media-query API when no test query is supplied", () => {
    const addEventListener = vi.fn();
    const removeEventListener = vi.fn();
    const matchMedia = vi.fn(() => ({
      matches: true,
      addEventListener,
      removeEventListener,
    }));
    vi.stubGlobal("matchMedia", matchMedia);
    const root = document.createElement("html");

    const view = render(
      <ThemeSwitcher
        root={root}
        storage={{ getItem: () => "system", setItem: vi.fn() }}
        themeColor={null}
      />,
    );

    expect(matchMedia).toHaveBeenCalledWith("(prefers-color-scheme: dark)");
    expect(root).toHaveAttribute("data-theme", "dark");
    expect(addEventListener).toHaveBeenCalledWith("change", expect.any(Function));
    view.unmount();
    expect(removeEventListener).toHaveBeenCalledWith("change", expect.any(Function));
    vi.unstubAllGlobals();
  });
});
