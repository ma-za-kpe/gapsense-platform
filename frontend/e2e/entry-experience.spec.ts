import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const coverageSettlingTimeoutMilliseconds = 7_500;
const curriculumMatrixTimeoutMilliseconds = 600_000;
const assessmentMatrixTimeoutMilliseconds = 120_000;
const themeStorageKey = "gapsense.theme-preference.v1";
const minimumSupportedViewportPixels = 320;
const httpOk = 200;
const httpNotFound = 404;
const maximumMissingArtifactResponseBytes = 256;
const minimumTargetPixels = 44;
const maximumMobilePageViewports = 8.5;
const officialLevelCount = 11;
const curriculumCellCount = 176;
const localCoopDiagnostic =
  "The Cross-Origin-Opener-Policy header has been ignored, because the URL's origin was untrustworthy.";

type CoverageIdentityPayload = {
  readonly catalog: {
    readonly evidence_cells: number;
  };
  readonly source_inventory: {
    readonly acquired_artifacts: number;
    readonly records: readonly {
      readonly identifier: string;
      readonly artifact_available: boolean;
      readonly artifact_pages: number | null;
    }[];
  };
  readonly countries: readonly {
    readonly code: string;
    readonly coverage_matrix: readonly {
      readonly phase: string;
      readonly level_identifier: string;
      readonly subject_identifier: string;
      readonly status: "missing" | "located" | "extracted";
    }[];
  }[];
};

type CurriculumDetailPayload = {
  readonly release_id: string;
  readonly country: string;
  readonly phase: string;
  readonly level: string;
  readonly subject: string;
  readonly extraction_status: "located" | "extracted";
  readonly extraction_method: string;
  readonly sections: readonly unknown[];
  readonly nodes: readonly unknown[];
};

const downloadText = async (download: import("@playwright/test").Download): Promise<string> => {
  const stream = await download.createReadStream();
  let contents = "";
  for await (const chunk of stream as AsyncIterable<Uint8Array>) {
    contents += Buffer.from(chunk).toString("utf8");
  }
  return contents;
};

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
      /unreviewed subject record|Evidence files exist, but no subject is publishable yet|No public evidence is available yet/,
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
  test.setTimeout(curriculumMatrixTimeoutMilliseconds);
  const response = await page.goto("/curriculum");

  expect(response?.ok()).toBe(true);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Inspect the public evidence boundary.",
  );
  const coverageResponse = await page.request.get("/api/v1/curriculum/coverage");
  expect(coverageResponse.ok()).toBe(true);
  const coveragePayload = (await coverageResponse.json()) as CoverageIdentityPayload;
  const country = page.getByRole("combobox", { name: "Country" });
  const level = page.getByRole("combobox", { name: "Level" });
  const subject = page.getByRole("combobox", { name: "Subject" });
  const detailStatus = page.locator(".curriculum-explorer__status");
  const visitedCells: string[] = [];
  await expect(subject).toBeVisible({
    timeout: coverageSettlingTimeoutMilliseconds,
  });
  const countryOptions = await country.locator("option").all();
  expect(countryOptions).toHaveLength(coveragePayload.countries.length);
  for (const option of countryOptions) {
    const countryCode = await option.getAttribute("value");
    if (countryCode === null) throw new Error("A curriculum country option has no value");
    await country.selectOption(countryCode);
    const expectedCountry = coveragePayload.countries.find((item) => item.code === countryCode);
    if (expectedCountry === undefined) throw new Error("A selector country is absent from the API");
    const expectedLevels = [
      ...new Set(expectedCountry.coverage_matrix.map((item) => item.level_identifier)),
    ];
    const levelOptions = await level.locator("option").all();
    expect(levelOptions).toHaveLength(expectedLevels.length);
    for (const levelOption of levelOptions) {
      const levelIdentifier = await levelOption.getAttribute("value");
      if (levelIdentifier === null) throw new Error("A curriculum level option has no value");
      await level.selectOption(levelIdentifier);
      const expectedSubjects = expectedCountry.coverage_matrix
        .filter((item) => item.level_identifier === levelIdentifier)
        .map((item) => item.subject_identifier)
        .sort();
      const subjectValues = await subject
        .locator("option")
        .evaluateAll((options) => options.map((item) => (item as HTMLOptionElement).value).sort());
      expect(subjectValues).toEqual(expectedSubjects);
      for (const subjectIdentifier of expectedSubjects) {
        const expectedEntry = expectedCountry.coverage_matrix.find(
          (item) =>
            item.level_identifier === levelIdentifier &&
            item.subject_identifier === subjectIdentifier,
        );
        if (expectedEntry === undefined) {
          throw new Error("A selector subject is absent from the API matrix");
        }
        await subject.selectOption(subjectIdentifier);
        await expect(subject).toHaveValue(subjectIdentifier);
        const countrySlug = countryCode === "GH" ? "ghana" : "uganda";
        const detailPath =
          `/api/v1/curriculum/${countrySlug}/${expectedEntry.phase}/` +
          `${levelIdentifier}/${subjectIdentifier}`;
        const detailResponse = await page.request.get(detailPath);
        if (expectedEntry.status === "missing") {
          expect(detailResponse.status(), detailPath).toBe(httpNotFound);
          expect((await detailResponse.body()).byteLength).toBeLessThanOrEqual(
            maximumMissingArtifactResponseBytes,
          );
          await expect(detailStatus).toHaveText(
            "This official curriculum area is catalogued, but release-qualified detail is unavailable.",
            { timeout: coverageSettlingTimeoutMilliseconds },
          );
          await expect(page.locator(".curriculum-tree")).toHaveCount(0);
          visitedCells.push(
            `${countryCode}:${expectedEntry.phase}:${levelIdentifier}:${subjectIdentifier}`,
          );
          continue;
        }
        expect(detailResponse.ok(), detailPath).toBe(true);
        const detailPayload = (await detailResponse.json()) as CurriculumDetailPayload;
        expect(detailPayload).toMatchObject({
          release_id: expect.any(String),
          country: countrySlug,
          phase: expectedEntry.phase,
          level: levelIdentifier,
          subject: subjectIdentifier,
          extraction_status: expectedEntry.status,
          extraction_method: expect.any(String),
        });
        await expect(detailStatus).toContainText(
          expectedEntry.status === "located"
            ? "Official curriculum area confirmed"
            : `Level evidence - extracted - ${String(detailPayload.nodes.length)} source pages`,
          { timeout: coverageSettlingTimeoutMilliseconds },
        );
        if (detailPayload.extraction_status === "located") {
          expect(detailPayload.sections).toHaveLength(0);
          expect(detailPayload.nodes).toHaveLength(0);
          await expect(
            page.getByRole("heading", { level: 2, name: /is represented$/ }),
          ).toBeVisible();
        } else {
          expect(detailPayload.sections.length).toBeGreaterThan(1);
          expect(detailPayload.nodes.length).toBeGreaterThan(0);
          await expect(page.locator(".curriculum-tree__section")).toHaveCount(
            detailPayload.sections.length,
          );
          await expect(page.locator(".curriculum-tree__nodes > details")).toHaveCount(
            detailPayload.nodes.length,
          );
          await expect(page.getByText(/^Text extraction:/)).toBeVisible();
        }
        await expect(page.locator(".curriculum-tree")).not.toContainText(
          /None recorded|no safe extracted detail/i,
        );
        visitedCells.push(
          `${countryCode}:${expectedEntry.phase}:${levelIdentifier}:${subjectIdentifier}`,
        );
      }
    }
  }
  expect(visitedCells).toHaveLength(curriculumCellCount);
  expect(new Set(visitedCells).size).toBe(curriculumCellCount);
  await expect(detailStatus).not.toContainText(/could not be loaded/i);
  const catalogue = page.getByRole("region", {
    name: "Every declared Ghana and Uganda curriculum area",
  });
  await expect(catalogue).toContainText("176 of 176");
  await expect(catalogue.locator(".curriculum-catalogue__levels details")).toHaveCount(
    officialLevelCount,
  );
  const curriculumCells = catalogue.locator("[data-curriculum-cell]");
  await expect(curriculumCells).toHaveCount(curriculumCellCount);
  await expect(catalogue.locator('a[href^="https://"]')).toHaveCount(officialLevelCount);
  await expect(catalogue).toContainText(
    `${String(coveragePayload.catalog.evidence_cells)} have evidence records`,
  );
  const expectedCellIdentities = coveragePayload.countries.flatMap((country) =>
    country.coverage_matrix.map(
      (entry) =>
        `${country.code}:${entry.phase}:${entry.level_identifier}:${entry.subject_identifier}`,
    ),
  );
  const renderedCellIdentities = await curriculumCells.evaluateAll((cells) =>
    cells.map((cell) => {
      const identity = cell.getAttribute("data-curriculum-cell");
      if (identity === null) throw new Error("A rendered curriculum cell has no identity");
      return identity;
    }),
  );
  expect(new Set(renderedCellIdentities).size).toBe(curriculumCellCount);
  expect([...renderedCellIdentities].sort()).toEqual([...expectedCellIdentities].sort());

  const sourceInventory = page.getByRole("region", {
    name: "Every release-qualified official source record",
  });
  const sourceRecordCount = coveragePayload.source_inventory.records.length;
  await expect(sourceInventory).toContainText(
    `${String(sourceRecordCount)} source records are accounted for`,
  );
  await expect(sourceInventory).toContainText(
    `${String(coveragePayload.source_inventory.acquired_artifacts)} have byte-verified artifacts`,
  );
  const sourceRecords = sourceInventory.locator("[data-source-record]");
  await expect(sourceRecords).toHaveCount(sourceRecordCount);
  await expect(sourceInventory.locator("li code")).toHaveCount(sourceRecordCount);
  await expect(sourceInventory.getByText(/^Retrieved /)).toHaveCount(sourceRecordCount);
  await expect(sourceInventory.getByText(/^Review: /)).toHaveCount(sourceRecordCount);
  await expect(sourceInventory.getByText(/^Rights: /)).toHaveCount(sourceRecordCount);
  await expect(sourceInventory.locator('li a[href^="https://"]')).toHaveCount(sourceRecordCount);
  await expect(sourceInventory.locator("li > p:not(.source-inventory__provenance)")).toHaveCount(
    sourceRecordCount,
  );
  const renderedSourceIdentities = await sourceRecords.evaluateAll((records) =>
    records.map((record) => {
      const identity = record.getAttribute("data-source-record");
      if (identity === null) throw new Error("A rendered source record has no identity");
      return identity;
    }),
  );
  expect(new Set(renderedSourceIdentities).size).toBe(sourceRecordCount);
  expect([...renderedSourceIdentities].sort()).toEqual(
    [...coveragePayload.source_inventory.records.map((record) => record.identifier)].sort(),
  );
  for (const record of coveragePayload.source_inventory.records) {
    const renderedRecord = sourceInventory.locator(`[data-source-record="${record.identifier}"]`);
    await expect(renderedRecord).toContainText(
      record.artifact_pages === null
        ? "Page count unavailable"
        : `${String(record.artifact_pages)} official pages`,
    );
    expect(record.artifact_available).toBe(record.artifact_pages !== null);
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

test("opens every supported role and country sample-creation path", async ({ page }) => {
  test.setTimeout(assessmentMatrixTimeoutMilliseconds);
  const combinations = [
    ["Teacher", "Ghana", "Ghana Basic 3 Science sample"],
    ["Teacher", "Uganda", "Uganda Primary 2 Mathematics sample"],
    ["Parent or caregiver", "Ghana", "Ghana Basic 3 Science sample"],
    ["Parent or caregiver", "Uganda", "Uganda Primary 2 Mathematics sample"],
    ["Learner", "Ghana", "Ghana Basic 3 Science sample"],
    ["Learner", "Uganda", "Uganda Primary 2 Mathematics sample"],
    ["Tutor", "Ghana", "Ghana Basic 3 Science sample"],
    ["Tutor", "Uganda", "Uganda Primary 2 Mathematics sample"],
  ] as const;

  for (const [role, country, heading] of combinations) {
    await page.goto("/#planner");
    await page.getByRole("radio", { name: new RegExp(`^${role}`) }).check();
    await page.getByRole("radio", { name: new RegExp(`^${country}`) }).check();
    await page.getByRole("radio", { name: /^Practice activity/ }).check();
    await page.getByRole("button", { name: "Review sample choice" }).click();
    await expect(
      page.getByRole("heading", { level: 3, name: `Your ${country} sample is ready` }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Open sample activity" }).click();
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
    await page.getByRole("button", { name: "Choose another sample" }).click();
    await expect(page.getByRole("button", { name: "Review sample choice" })).toBeDisabled();
  }
});

test("delivers separate real learner and educator downloads from a reviewed sample", async ({
  page,
}) => {
  await page.goto("/#planner");
  await page.getByRole("radio", { name: /^Teacher/ }).check();
  await page.getByRole("radio", { name: /^Ghana/ }).check();
  await expect(page.getByRole("radio", { name: /^Diagnostic pathway/ })).toBeDisabled();
  await expect(page.getByRole("radio", { name: /^Assessment package/ })).toBeDisabled();
  await page.getByRole("radio", { name: /^Practice activity/ }).check();
  await page.getByRole("button", { name: "Review sample choice" }).click();
  await page.getByRole("button", { name: "Open sample activity" }).click();

  const learnerDownloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download learner worksheet" }).click();
  const learnerDownload = await learnerDownloadPromise;
  expect(learnerDownload.suggestedFilename()).toBe("gapsense-learner-worksheet.html");
  const learnerDocument = await downloadText(learnerDownload);
  expect(learnerDocument).toContain("Ghana Basic 3 Science sample");
  expect(learnerDocument).toContain("Name one source of light.");
  expect(learnerDocument).not.toContain("Answer guidance:");

  const educatorDownloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download answer guide" }).click();
  const educatorDownload = await educatorDownloadPromise;
  expect(educatorDownload.suggestedFilename()).toBe("gapsense-answer-guide.html");
  const educatorDocument = await downloadText(educatorDownload);
  expect(educatorDocument).toContain("Ghana Basic 3 Science sample");
  expect(educatorDocument).toContain("Answer guidance:");
  expect(educatorDocument).toContain("The sun, a lamp, or another reasonable source");
  expect(await learnerDownload.failure()).toBeNull();
  expect(await educatorDownload.failure()).toBeNull();
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

  for (const path of [
    "/",
    "/curriculum",
    "/about",
    "/evidence",
    "/privacy",
    "/terms",
    "/assessment",
  ]) {
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

  for (const trustRoute of [
    {
      path: "/evidence",
      title: "Evidence and limitations \u2014 GapSense",
      heading: "Evidence, limitations, and known blockers.",
    },
    {
      path: "/privacy",
      title: "Privacy policy \u2014 GapSense",
      heading: "Privacy without surveillance.",
    },
    {
      path: "/terms",
      title: "Terms of use \u2014 GapSense",
      heading: "Use GapSense with evidence and care.",
    },
  ]) {
    const response = await page.goto(trustRoute.path);
    expect(response?.ok()).toBe(true);
    await expect(page).toHaveTitle(trustRoute.title);
    await expect(page.getByRole("heading", { level: 1, name: trustRoute.heading })).toBeVisible();
    await expect(page.getByRole("navigation", { name: /contents/i })).toBeVisible();
    await expectNoAccessibilityViolations(page);
  }
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
