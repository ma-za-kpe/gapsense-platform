import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const coverageSettlingTimeoutMilliseconds = 7_500;
const themeStorageKey = "gapsense.theme-preference.v1";
const minimumSupportedViewportPixels = 320;
const httpOk = 200;
const httpNotFound = 404;
const maximumMissingArtifactResponseBytes = 256;
const minimumTargetPixels = 44;
const maximumMobilePageViewports = 8.5;
const localCoopDiagnostic =
  "The Cross-Origin-Opener-Policy header has been ignored, because the URL's origin was untrustworthy.";

const chooseTheme = async (
  page: import("@playwright/test").Page,
  value: "light" | "dark" | "system",
  label: "Light" | "Dark" | "System",
): Promise<void> => {
  const compactControl = page.getByRole("combobox", { name: "Theme" });
  if (await compactControl.isVisible()) {
    await compactControl.selectOption(value);
    return;
  }
  await page.getByRole("radio", { name: label }).check();
};

const expectCoverageEvidence = async (page: import("@playwright/test").Page): Promise<void> => {
  await expect(
    page.getByText(
      /unreviewed subject record|Evidence files exist, but no subject is publishable yet/,
    ),
  ).toHaveCount(2, { timeout: coverageSettlingTimeoutMilliseconds });
};

const expectNoAccessibilityViolations = async (
  page: import("@playwright/test").Page,
): Promise<void> => {
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
};

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
});

test("never offers a blank curriculum combination", async ({ page }) => {
  const response = await page.goto("/curriculum");

  expect(response?.ok()).toBe(true);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Inspect the public evidence boundary.",
  );
  const subject = page.getByRole("combobox", { name: "Subject" });
  const emptyState = page.getByRole("heading", {
    level: 2,
    name: "No public subject evidence is available yet",
  });
  await expect(subject.or(emptyState)).toBeVisible({
    timeout: coverageSettlingTimeoutMilliseconds,
  });
  if ((await subject.count()) === 0) {
    await expect(emptyState).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Read how evidence is published" }),
    ).toHaveAttribute("href", "/about#evidence");
  } else {
    const country = page.getByRole("combobox", { name: "Country" });
    const countryOptions = await country.locator("option").all();
    for (const option of countryOptions) {
      const value = await option.getAttribute("value");
      if (value === null) throw new Error("A curriculum country option has no value");
      await country.selectOption(value);
      await expect(page.getByRole("combobox", { name: "Level" }).locator("option")).not.toHaveCount(
        0,
      );
      await expect(subject.locator("option")).not.toHaveCount(0);
    }
    await expect(page.getByText(/\d+ standards/).first()).toBeVisible();
  }
  await expectNoAccessibilityViolations(page);
});

test("renders the prerequisite-gap mission without presenting the product model as a diagnosis", async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const analyticsRequests: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/v1/analytics/events") {
      analyticsRequests.push(request.url());
    }
  });

  const response = await page.goto("/");

  expect(response?.ok()).toBe(true);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Find the next learning step.");
  await expect(page.getByText("Find the gap. See the reason. Take the next step.")).toBeVisible();
  await expect(
    page.getByText(/help educators identify the earliest learning prerequisite/i),
  ).toBeVisible();
  const model = page.getByRole("figure", { name: "Illustrative learning path" });
  await expect(model).toBeVisible();
  await expect(model.getByText("Product model")).toBeVisible();
  await expect(model.getByText("Fractions")).toBeVisible();
  await expect(model.getByText("Equal groups")).toBeVisible();
  await expect(model.getByText("Counting")).toBeVisible();
  await expect(model.getByText("Visual grouping practice")).toBeVisible();
  await expect(
    model.getByText(
      "Example only — not a learner diagnosis or a claim about current curriculum coverage.",
    ),
  ).toBeVisible();
  await expect(model).not.toContainText(/92|confidence/i);
  await expect(
    page.getByText(/Today, the public release offers clearly labelled activity samples/i),
  ).toBeVisible();
  await expect(page.getByText("Public evidence catalogue connected")).toBeVisible();
  await expectCoverageEvidence(page);
  await expect(page.getByText("No educator review has been recorded.")).toHaveCount(2);
  await expect(
    page.getByText("No account. No learner data. No hidden AI dependency."),
  ).toBeVisible();
  await expect(page.locator(".hero__kicker").getByRole("link", { name: "Maku" })).toHaveAttribute(
    "href",
    "https://startuptribunal.com/maku",
  );
  await expect(page.locator("body")).not.toContainText(/UNICEF|local evidence mount|Ollama/i);

  await expectNoAccessibilityViolations(page);
  const pageUrl = new URL(page.url());
  const actionableConsoleErrors = consoleErrors.filter(
    (message) =>
      !(
        pageUrl.protocol === "http:" &&
        pageUrl.hostname !== "localhost" &&
        message.startsWith(localCoopDiagnostic)
      ),
  );
  expect(actionableConsoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(analyticsRequests).toEqual([]);
});

test("persists an anonymous Uganda sample and supports a clean restart", async ({ page }) => {
  await page.goto("/#planner");
  const review = page.getByRole("button", { name: "Review sample choice" });

  await expect(review).toBeDisabled();
  await page.getByRole("radio", { name: /^Parent or caregiver/ }).check();
  await page.getByRole("radio", { name: /^Uganda/ }).check();
  await expect(review).toBeDisabled();
  await page.getByRole("radio", { name: /^Practice activity/ }).check();
  await expect(review).toBeEnabled();
  await review.click();
  await expect(
    page.getByRole("heading", { level: 3, name: "Your Uganda sample is ready" }),
  ).toBeVisible();
  await expect(
    page.getByText("Illustrative GapSense sample; not curriculum-aligned or educator-reviewed."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open sample activity" }).click();

  await expect(page).toHaveURL(/\/assessment$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "Uganda Primary 2 Mathematics sample" }),
  ).toBeVisible();
  await expect(page.getByText("Write the number that comes immediately after 19.")).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { level: 1, name: "Uganda Primary 2 Mathematics sample" }),
  ).toBeVisible();
  await page.getByText("Show answer guidance").click();
  await expect(page.getByText(/20/).first()).toBeVisible();
  await page.getByRole("button", { name: "Choose another sample" }).click();

  await expect(page).toHaveURL(/\/#planner$/);
  await expect(page.getByRole("button", { name: "Review sample choice" })).toBeDisabled();
});

test("preserves keyboard focus, touch sizing, and a compact responsive layout", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const skipLink = page.getByRole("link", { name: "Skip to main content" });
  await expect(skipLink).toBeFocused();
  expect(await skipLink.evaluate((element) => getComputedStyle(element).outlineStyle)).not.toBe(
    "none",
  );

  const layout = await page.evaluate(() => ({
    documentHeight: document.documentElement.scrollHeight,
    documentWidth: document.documentElement.scrollWidth,
    targetHeights: [...document.querySelectorAll<HTMLElement>("a, button, summary, select")]
      .filter((element) => {
        const bounds = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return bounds.width > 0 && bounds.height > 0 && style.visibility !== "hidden";
      })
      .map((element) => ({
        height: element.getBoundingClientRect().height,
        label: element.innerText.trim() || element.tagName,
      })),
    viewportHeight: document.documentElement.clientHeight,
    viewportWidth: document.documentElement.clientWidth,
  }));
  expect(layout.documentWidth).toBeLessThanOrEqual(layout.viewportWidth);
  for (const target of layout.targetHeights) {
    expect
      .soft(target.height, `${target.label} touch target`)
      .toBeGreaterThanOrEqual(minimumTargetPixels);
  }

  if (testInfo.project.name === "mobile-chromium") {
    expect(layout.documentHeight / layout.viewportHeight).toBeLessThanOrEqual(
      maximumMobilePageViewports,
    );
    await expect(page.getByRole("combobox", { name: "Theme" })).toBeVisible();
    await expect(page.locator(".site-header .brand__word")).toBeVisible();
    await page.getByText("Menu", { exact: true }).click();
    await expect(
      page.getByRole("navigation", { name: "Mobile navigation" }).getByRole("link", {
        name: "Curriculum",
      }),
    ).toBeVisible();
  } else {
    await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
    await expect(page.getByRole("group", { name: "Theme" })).toBeVisible();
  }
});

test("switches, persists, and follows the operating-system theme without storing personal data", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");
  const root = page.locator("html");
  const compactControl = page.getByRole("combobox", { name: "Theme" });
  if (await compactControl.isVisible()) {
    await expect(compactControl).toHaveValue("system");
  } else {
    await expect(page.getByRole("group", { name: "Theme" })).toBeVisible();
  }
  await expect(root).toHaveAttribute("data-theme-preference", "system");
  await expect(root).toHaveAttribute("data-theme", "light");

  await chooseTheme(page, "dark", "Dark");
  await expect(root).toHaveAttribute("data-theme-preference", "dark");
  await expect(root).toHaveAttribute("data-theme", "dark");
  expect(await page.evaluate((key) => localStorage.getItem(key), themeStorageKey)).toBe("dark");

  await page.reload();
  await expect(root).toHaveAttribute("data-theme", "dark");
  await chooseTheme(page, "light", "Light");
  await expect(root).toHaveAttribute("data-theme", "light");

  await page.emulateMedia({ colorScheme: "dark" });
  await chooseTheme(page, "system", "System");
  await expect(root).toHaveAttribute("data-theme-preference", "system");
  await expect(root).toHaveAttribute("data-theme", "dark");
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([themeStorageKey]);
});

test("applies a stored dark theme before the application module can render", async ({ page }) => {
  await page.addInitScript(
    ({ key }) => {
      localStorage.setItem(key, "dark");
    },
    { key: themeStorageKey },
  );
  await page.route("**/*", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.resourceType() === "script" && path !== "/theme-init.js") {
      await route.abort();
      return;
    }
    await route.continue();
  });

  await page.goto("/");

  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme-preference", "dark");
  await expect(page.locator("#root")).toBeEmpty();
});

test("keeps selection and disabled actions visible in forced-colour mode", async ({ page }) => {
  await page.emulateMedia({ forcedColors: "active" });
  await page.goto("/");

  const compactControl = page.getByRole("combobox", { name: "Theme" });
  if (await compactControl.isVisible()) {
    await expect(compactControl).toHaveValue("system");
    expect(await compactControl.evaluate((element) => getComputedStyle(element).borderStyle)).toBe(
      "solid",
    );
  } else {
    const systemOption = page.getByRole("radio", { name: "System" });
    await expect(systemOption).toBeChecked();
    expect(
      await page.locator('.theme-switcher input[value="system"] + span').evaluate((element) => {
        return getComputedStyle(element).outlineStyle;
      }),
    ).not.toBe("none");
  }

  const disabledAction = page.getByRole("button", { name: "Review sample choice" });
  await expect(disabledAction).toBeDisabled();
  expect(
    await disabledAction.evaluate((element) => ({
      borderStyle: getComputedStyle(element).borderStyle,
      opacity: getComputedStyle(element).opacity,
    })),
  ).toEqual({ borderStyle: "dashed", opacity: "1" });
});

test("keeps every public route accessible in explicit dark mode", async ({ page }) => {
  await page.addInitScript(
    ({ key }) => {
      localStorage.setItem(key, "dark");
    },
    { key: themeStorageKey },
  );

  for (const path of ["/", "/curriculum", "/about", "/assessment"]) {
    await page.goto(path);
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await expectNoAccessibilityViolations(page);
  }
});

test("reflows the complete entry experience at 320 pixels", async ({ page }) => {
  await page.setViewportSize({
    width: minimumSupportedViewportPixels,
    height: 900,
  });
  await page.goto("/");
  const layout = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(layout.clientWidth).toBe(minimumSupportedViewportPixels);
  expect(layout.scrollWidth).toBeLessThanOrEqual(minimumSupportedViewportPixels);
  await expect(page.getByRole("combobox", { name: "Theme" })).toBeVisible();
  await expect(page.getByText("Start with intent")).toBeVisible();
});

test("serves distinct trust routes and recoverable deep links", async ({ page }) => {
  const assessmentResponse = await page.goto("/assessment");
  expect(assessmentResponse?.ok()).toBe(true);
  await expect(page).toHaveTitle("Activity sample \u2014 GapSense");
  await expect(
    page.getByRole("heading", { level: 1, name: "No saved sample activity" }),
  ).toBeVisible();

  const aboutResponse = await page.goto("/about");
  expect(aboutResponse?.ok()).toBe(true);
  await expect(page).toHaveTitle("Trust and evidence \u2014 GapSense");
  await expect(
    page.getByRole("heading", { level: 1, name: "How GapSense earns trust." }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evidence and review" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Privacy and saved choices" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Accessibility commitment" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Feedback and correction" })).toBeVisible();
  await expectNoAccessibilityViolations(page);
});

test("serves a hardened same-origin surface", async ({ page }) => {
  const response = await page.goto("/");
  const moduleSource = await page.locator("script[type='module']").last().getAttribute("src");
  const robots = await page.request.get("/robots.txt");
  const sitemap = await page.request.get("/sitemap.xml");

  await expect(page).toHaveTitle("GapSense \u2014 Find the next learning step");
  await expect(page.locator('meta[name="description"]')).toHaveAttribute(
    "content",
    "See how GapSense connects observed difficulty, curriculum prerequisites, and practical next steps while keeping current evidence limits explicit.",
  );
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
    "content",
    "noindex, nofollow, noarchive",
  );
  await expect(page.locator('meta[property="og:site_name"]')).toHaveAttribute(
    "content",
    "GapSense",
  );
  await expect(page.locator('link[rel="canonical"]')).toHaveCount(0);
  await expect(page.locator('script[type="application/ld+json"]')).toHaveCount(0);
  expect(robots.status()).toBe(httpOk);
  expect(await robots.text()).toBe("User-agent: *\nDisallow: /\n");
  expect(sitemap.status()).toBe(httpNotFound);
  expect(sitemap.headers()["content-type"]).toContain("text/plain");
  const sitemapBody = await sitemap.text();
  expect(sitemapBody).not.toMatch(/<urlset|<html/i);
  expect(sitemapBody.length).toBeLessThanOrEqual(maximumMissingArtifactResponseBytes);
  expect(response?.headers()["content-security-policy"]).toContain("default-src 'self'");
  expect(response?.headers()["cross-origin-opener-policy"]).toBe("same-origin");
  expect(response?.headers()["permissions-policy"]).toContain("camera=()");
  expect(response?.headers()["referrer-policy"]).toBe("no-referrer");
  expect(response?.headers()["x-content-type-options"]).toBe("nosniff");
  expect(response?.headers()["x-frame-options"]).toBe("DENY");
  if (moduleSource === null) {
    throw new Error("the rendered page did not reference its application module");
  }

  const applicationModule = await page.request.get(moduleSource);
  expect(applicationModule.ok()).toBe(true);
  expect(applicationModule.headers()["content-security-policy"]).toContain("default-src 'self'");
  expect(applicationModule.headers()["x-content-type-options"]).toBe("nosniff");
  if (process.env.EXPECT_IMMUTABLE_ASSETS === "1") {
    expect(applicationModule.headers()["cache-control"]).toBe(
      "public, max-age=31536000, immutable",
    );
  }
});

test("matches the reviewed system-theme entry-experience baseline", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Public evidence catalogue connected")).toBeVisible();
  await expectCoverageEvidence(page);
  await expect(page).toHaveScreenshot("entry-experience.png", {
    fullPage: true,
    timeout: 15_000,
  });
});

test("matches the reviewed explicit-light entry-experience baseline", async ({ page }) => {
  await page.addInitScript(
    ({ key }) => {
      localStorage.setItem(key, "light");
    },
    { key: themeStorageKey },
  );
  await page.goto("/");
  await expect(page.getByText("Public evidence catalogue connected")).toBeVisible();
  await expectCoverageEvidence(page);
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(page).toHaveScreenshot("entry-experience-light.png", {
    fullPage: true,
    timeout: 15_000,
  });
});

test("matches the reviewed explicit-dark entry-experience baseline", async ({ page }) => {
  await page.addInitScript(
    ({ key }) => {
      localStorage.setItem(key, "dark");
    },
    { key: themeStorageKey },
  );
  await page.goto("/");
  await expect(page.getByText("Public evidence catalogue connected")).toBeVisible();
  await expectCoverageEvidence(page);
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page).toHaveScreenshot("entry-experience-dark.png", {
    fullPage: true,
    timeout: 15_000,
  });
});
