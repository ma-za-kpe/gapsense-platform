import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const coverageSettlingTimeoutMilliseconds = 7_500;
const httpOk = 200;
const httpNotFound = 404;
const maximumMissingArtifactResponseBytes = 256;
const minimumTargetPixels = 44;
const maximumMobilePageViewports = 8.5;

const expectCoverageEvidence = async (page: import("@playwright/test").Page): Promise<void> => {
  await expect(page.getByText(/\d+ repository files? located/)).toHaveCount(2, {
    timeout: coverageSettlingTimeoutMilliseconds,
  });
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
  if ((await subject.count()) === 0) {
    await expect(
      page.getByRole("heading", {
        level: 2,
        name: "No public subject evidence is available yet",
      }),
    ).toBeVisible();
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

test("renders a truthful, quiet Ghana and Uganda entry experience", async ({ page }) => {
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
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "See the evidence. Try an honest sample.",
  );
  await expect(page.getByText("Country coverage")).toBeVisible();
  await expect(page.getByText("Illustrative activity", { exact: true })).toBeVisible();
  await expect(page.getByText("Diagnosis", { exact: true })).toBeVisible();
  await expect(page.getByText("Not available", { exact: true })).toBeVisible();
  await expect(page.getByText("Public evidence catalogue connected")).toBeVisible();
  await expectCoverageEvidence(page);
  await expect(page.getByText("Extraction and educator review not verified")).toHaveCount(2);
  await expect(
    page.getByText("No account, name, school, or learner response is requested."),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Maku" })).toHaveAttribute(
    "href",
    "https://startuptribunal.com/maku",
  );
  await expect(page.locator("body")).not.toContainText(
    /UNICEF|Find the next learning step|Earliest gap|local evidence mount|Ollama/i,
  );

  await expectNoAccessibilityViolations(page);
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(analyticsRequests).toEqual([]);
});

test("persists an anonymous Uganda sample and supports a clean restart", async ({ page }) => {
  await page.goto("/#planner");
  const review = page.getByRole("button", { name: "Review sample choice" });

  await expect(review).toBeDisabled();
  await page.getByRole("radio", { name: /^Parent or caregiver/ }).check();
  await page.getByRole("radio", { name: /^Uganda/ }).check();
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
    await page.getByText("Menu", { exact: true }).click();
    await expect(
      page.getByRole("navigation", { name: "Mobile navigation" }).getByRole("link", {
        name: "Curriculum",
      }),
    ).toBeVisible();
  } else {
    await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
  }
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

  await expect(page).toHaveTitle("GapSense \u2014 Evidence and honest activity samples");
  await expect(page.locator('meta[name="description"]')).toHaveAttribute(
    "content",
    "Inspect public curriculum evidence for Ghana and Uganda, then try a clearly labelled illustrative activity sample.",
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

test("matches the reviewed entry-experience baseline", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Public evidence catalogue connected")).toBeVisible();
  await expectCoverageEvidence(page);
  await expect(page).toHaveScreenshot("entry-experience.png", {
    fullPage: true,
    timeout: 15_000,
  });
});
