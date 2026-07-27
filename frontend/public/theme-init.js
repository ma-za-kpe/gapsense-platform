(() => {
  const storageKey = "gapsense.theme-preference.v1";
  let preference = "system";
  try {
    const stored = window.localStorage.getItem(storageKey);
    if (stored === "light" || stored === "dark" || stored === "system") {
      preference = stored;
    }
  } catch {
    preference = "system";
  }
  const systemUsesDark =
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;
  const resolved = preference === "system" ? (systemUsesDark ? "dark" : "light") : preference;
  document.documentElement.dataset.theme = resolved;
  document.documentElement.dataset.themePreference = preference;
  document.documentElement.style.colorScheme = resolved;
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor !== null) {
    themeColor.setAttribute("content", resolved === "dark" ? "#102a27" : "#fbfcf8");
  }
})();
