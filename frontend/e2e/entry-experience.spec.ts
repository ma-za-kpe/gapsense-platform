import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const coverageSettlingTimeoutMilliseconds = 7_500;
const httpOk = 200;
const httpNotFound = 404;

const expectCoverageEvidence = async (page: import("@playwright/test").Page): Promise<void> => {
  await expect(page.getByText(/\d+ repository files? located/)).toHaveCount(2, {
    timeout: coverageSettlingTimeoutMilliseconds,
  });
};

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
});

test("renders a truthful, accessible Ghana and Uganda entry experience", async ({ page }) => {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const analyticsRequests: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    pageErrors.push(error.message);
  });
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/v1/analytics/events") {
      analyticsRequests.push(request.url());
    }
  });

  const response = await page.goto("/");

  expect(response?.ok()).toBe(true);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Find the next learning step.");
  await expect(page.getByRole("heading", { level: 3, name: "Ghana" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 3, name: "Uganda" })).toBeVisible();
  await expect(page.getByText("Curriculum evidence connected")).toBeVisible();
  await expectCoverageEvidence(page);
  await expect(page.getByText("Extraction and educator review not verified")).toHaveCount(2);
  await expect(
    page.getByText("No account. No learner data. No hidden AI dependency."),
  ).toBeVisible();
  await expect(page.getByText(/Built by Maku for Africa\./)).toBeVisible();
  await expect(
    page.getByText("Built by Maku for Africa, grounded first in Ghana and Uganda."),
  ).toBeVisible();
  await expect(page.locator("body")).not.toContainText(/UNICEF/i);

  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(analyticsRequests).toEqual([]);
});

test("plans an anonymous Uganda activity and supports a clean restart", async ({ page }) => {
  await page.goto("/#planner");
  const review = page.getByRole("button", { name: "Review my starting point" });

  await expect(review).toBeDisabled();
  await page
    .getByRole("group", { name: /Who are you planning for/ })
    .getByText("Parent or caregiver", { exact: true })
    .click();
  await page
    .getByRole("group", { name: /Choose the education system/ })
    .getByText("Uganda", { exact: true })
    .click();
  await page
    .getByRole("group", { name: /What should this help you do/ })
    .getByText("Practice activity", { exact: true })
    .click();
  await expect(review).toBeEnabled();
  await review.click();

  await expect(
    page.getByRole("heading", { level: 3, name: "Your Uganda starting point is ready" }),
  ).toBeVisible();
  await expect(page.getByText(/NCDC curriculum inventory is still being verified/)).toBeVisible();
  await page.getByRole("button", { name: "Start again" }).click();
  await expect(review).toBeDisabled();
});

test("preserves keyboard focus, touch sizing, responsive layout, and reduced motion", async ({
  page,
}) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const skipLink = page.getByRole("link", { name: "Skip to main content" });
  await expect(skipLink).toBeFocused();
  expect(await skipLink.evaluate((element) => getComputedStyle(element).outlineStyle)).not.toBe(
    "none",
  );

  const viewport = page.viewportSize();
  expect(viewport).not.toBeNull();
  const layout = await page.evaluate(() => {
    const rootStyles = getComputedStyle(document.documentElement);
    const minimumCountryEvidenceSpacing =
      Number.parseFloat(rootStyles.getPropertyValue("--space-6")) *
      Number.parseFloat(rootStyles.fontSize);
    return {
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
      reviewHeight: document
        .querySelector<HTMLButtonElement>("button[type='submit']")
        ?.getBoundingClientRect().height,
      reducedMotionDuration: (() => {
        const reveal = document.querySelector(".reveal");
        return reveal instanceof HTMLElement ? getComputedStyle(reveal).animationDuration : null;
      })(),
      minimumCountryEvidenceSpacing,
      countryPanelLayout: [...document.querySelectorAll<HTMLElement>(".country-panel")].map(
        (panel) => {
          const levels = panel.querySelector<HTMLElement>("ul");
          const status = panel.querySelector<HTMLElement>(".country-panel__status");
          if (levels === null || status === null) {
            throw new Error("country panel is missing its level list or evidence status");
          }
          const panelBounds = panel.getBoundingClientRect();
          const levelBounds = levels.getBoundingClientRect();
          const statusBounds = status.getBoundingClientRect();
          return {
            levelStatusGap: statusBounds.top - levelBounds.bottom,
            panelStatusGap: panelBounds.bottom - statusBounds.bottom,
          };
        },
      ),
    };
  });
  expect(layout.documentWidth).toBeLessThanOrEqual(layout.viewportWidth);
  expect(layout.reviewHeight).toBeGreaterThanOrEqual(44);
  expect(["0.01ms", "1e-05s"]).toContain(layout.reducedMotionDuration);
  for (const panel of layout.countryPanelLayout) {
    expect(panel.levelStatusGap).toBeGreaterThanOrEqual(layout.minimumCountryEvidenceSpacing);
    expect(panel.panelStatusGap).toBeGreaterThanOrEqual(layout.minimumCountryEvidenceSpacing);
  }
});

test("serves a hardened same-origin surface", async ({ page }) => {
  const response = await page.goto("/");
  const moduleSource = await page.locator("script[type='module']").last().getAttribute("src");
  const robots = await page.request.get("/robots.txt");
  const sitemap = await page.request.get("/sitemap.xml");

  await expect(page).toHaveTitle("GapSense — Find the next learning step");
  await expect(page.locator('meta[name="description"]')).toHaveAttribute(
    "content",
    "GapSense helps Ghanaian and Ugandan learning communities plan curriculum-aligned assessments and find the next useful learning step.",
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
  expect(await sitemap.text()).toBe("Not found\n");
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
  await expect(page.getByText("Curriculum evidence connected")).toBeVisible();
  await expectCoverageEvidence(page);
  await expect(page).toHaveScreenshot("entry-experience.png", { fullPage: true });
});
