import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoveragePanels } from "./CoveragePanels";

const report = {
  repository_status: "available",
  complete: false,
  warnings: [],
  snapshot: {
    generated_at: "2026-07-27T17:00:00Z",
    source_version: null,
    review_status: "not_verified",
  },
  countries: [
    {
      code: "GH",
      name: "Ghana",
      authority: "National Council for Curriculum and Assessment (NaCCA)",
      authority_url: "https://nacca.gov.gh/curriculum/",
      availability: "present_unverified",
      review_status: "not_verified",
      repository_file_count: 1,
      levels: [
        {
          identifier: "lower_primary",
          name: "Lower Primary",
          official_phase: "Key Phase 2 (Basic 1–3)",
          review_status: "not_verified",
        },
      ],
      subjects: [
        {
          identifier: "mathematics",
          name: "Mathematics",
          phase: "primary",
          availability: "present_unverified",
          review_status: "not_verified",
        },
      ],
      coverage_matrix: [
        {
          level_identifier: "lower_primary",
          level_name: "Lower Primary",
          phase: "primary",
          subject_identifier: "mathematics",
          subject_name: "Mathematics",
          status: "missing",
          evidence_scope: "phase_only",
        },
        {
          level_identifier: "lower_primary_level",
          level_name: "Lower Primary",
          phase: "primary",
          subject_identifier: "science",
          subject_name: "Science",
          status: "located",
          evidence_scope: "level",
        },
        {
          level_identifier: "upper_primary",
          level_name: "Upper Primary",
          phase: "primary",
          subject_identifier: "english",
          subject_name: "English",
          status: "extracted",
          evidence_scope: "phase_only",
        },
      ],
    },
    {
      code: "UG",
      name: "Uganda",
      authority: "National Curriculum Development Centre (NCDC)",
      authority_url: "https://ncdc.go.ug/directorates/",
      availability: "missing",
      review_status: "not_verified",
      repository_file_count: 0,
      levels: [],
    },
  ],
} as const;

describe("coverage panels", () => {
  it("shows a stable two-country skeleton while loading", () => {
    render(<CoveragePanels state={{ status: "loading" }} onRetry={vi.fn()} />);

    expect(screen.getByRole("heading", { level: 3, name: "Ghana" })).toBeVisible();
    expect(screen.getByRole("heading", { level: 3, name: "Uganda" })).toBeVisible();
    expect(screen.getAllByText("Checking public coverage evidence…")).toHaveLength(2);
  });

  it("explains publishable evidence separately from internal file presence", async () => {
    render(<CoveragePanels state={{ status: "loaded", report }} onRetry={vi.fn()} />);

    expect(screen.getByText("1 unreviewed subject record is visible")).toBeVisible();
    expect(screen.getByText("No public evidence is available yet")).toBeVisible();
    expect(screen.queryByText(/repository files? located/)).not.toBeInTheDocument();
    expect(screen.getAllByText("Lower Primary").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Mathematics").length).toBeGreaterThan(0);
    await userEvent.setup().click(screen.getByText("See level and subject evidence matrix"));
    expect(screen.getAllByText("phase folder only").length).toBeGreaterThan(0);
    expect(screen.getByText("level folder")).toBeVisible();
    expect(screen.getAllByText("No educator review has been recorded.")).toHaveLength(2);
    await userEvent.setup().click(screen.getByText("See level and subject evidence matrix"));
  });

  it("explains when files exist but no subject is publishable", () => {
    const unpublishedReport = {
      ...report,
      countries: [{ ...report.countries[0], subjects: [] }],
    };
    render(
      <CoveragePanels state={{ status: "loaded", report: unpublishedReport }} onRetry={vi.fn()} />,
    );

    expect(
      screen.getByText("Evidence files exist, but no subject is publishable yet"),
    ).toBeVisible();
  });

  it("treats a legacy report without a subjects field as unpublished", () => {
    const legacyCountry = { ...report.countries[0] };
    Reflect.deleteProperty(legacyCountry, "subjects");
    const legacyReport = {
      ...report,
      countries: [legacyCountry],
    };

    render(<CoveragePanels state={{ status: "loaded", report: legacyReport }} onRetry={vi.fn()} />);

    expect(
      screen.getByText("Evidence files exist, but no subject is publishable yet"),
    ).toBeVisible();
  });

  it("explains the evidence-to-question organization for teachers", async () => {
    const user = userEvent.setup();
    render(<CoveragePanels state={{ status: "loaded", report }} onRetry={vi.fn()} />);

    const firstToggle = screen.getAllByText("See planned evidence structure").at(0);
    if (firstToggle === undefined) {
      throw new Error("Ghana curriculum map toggle was not rendered");
    }
    await user.click(firstToggle);

    expect(screen.getByText("Planned NaCCA evidence structure")).toBeVisible();
    expect(screen.getByText("Content standard and indicator")).toBeVisible();
    expect(
      screen.getByText(/intended organization for future reviewed Ghana evidence/i),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: /Open Ghana authority source/ })).toHaveAttribute(
      "href",
      "https://nacca.gov.gh/curriculum/",
    );
  });

  it("surfaces snapshot freshness and missing source-version provenance", () => {
    render(<CoveragePanels state={{ status: "loaded", report }} onRetry={vi.fn()} />);

    expect(screen.getByRole("note", { name: "Evidence snapshot" })).toHaveTextContent(
      "Catalogue checked 27 Jul 2026",
    );
    expect(screen.getByRole("note", { name: "Evidence snapshot" })).toHaveTextContent(
      "Official source version is not recorded",
    );
  });

  it("shows a recorded source version and plural publishable-subject count", () => {
    const firstCountry = report.countries[0];
    const versionedReport = {
      ...report,
      snapshot: { ...report.snapshot, source_version: "NaCCA 2019" },
      countries: [
        {
          ...firstCountry,
          subjects: [
            ...firstCountry.subjects,
            {
              ...firstCountry.subjects[0],
              identifier: "science",
              name: "Science",
            },
          ],
        },
      ],
    };

    render(
      <CoveragePanels state={{ status: "loaded", report: versionedReport }} onRetry={vi.fn()} />,
    );

    expect(screen.getByText("2 unreviewed subject records are visible")).toBeVisible();
    expect(screen.getByRole("note", { name: "Evidence snapshot" })).toHaveTextContent(
      "Official source version: NaCCA 2019",
    );
  });

  it("keeps country context visible and supports recovery when unavailable", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(<CoveragePanels state={{ status: "unavailable" }} onRetry={onRetry} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Public coverage details are unavailable");
    await user.click(screen.getByRole("button", { name: "Retry coverage details" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
