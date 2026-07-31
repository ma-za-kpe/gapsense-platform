import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoveragePanels } from "./CoveragePanels";
import type { CurriculumCoverageReport } from "../services/coverage";

const report = {
  repository_status: "available",
  complete: false,
  warnings: [],
  snapshot: {
    generated_at: "2026-07-27T17:00:00Z",
    source_version: "curriculum-2026-07-29-candidate.1",
    review_status: "not_verified",
  },
  catalog: {
    as_of: "2026-07-29",
    scope_status: "official_authority_inventory",
    represented_cells: 3,
    total_cells: 3,
    evidence_cells: 2,
  },
  source_inventory: {
    as_of: "2026-07-23",
    total_records: 1,
    acquired_artifacts: 0,
    records: [
      {
        identifier: "gh-jhs-official-index-current",
        country: "GH",
        phase: "secondary",
        level: "JHS1-JHS3",
        subject: "all",
        edition: "current index",
        source_url: "https://nacca.gov.gh/common-core-programme-ccp/",
        retrieved_on: "2026-07-23",
        license_status: "official_index_only_document_not_licensed_for_redistribution",
        artifact_available: false,
        artifact_pages: null,
        extraction_status: "index_only",
        review_status: "official_index_verified",
        known_gap: "Document records remain.",
      },
    ],
  },
  countries: [
    {
      code: "GH",
      name: "Ghana",
      authority: "National Council for Curriculum and Assessment (NaCCA)",
      authority_url: "https://nacca.gov.gh/curriculum/",
      availability: "present_unverified",
      review_status: "not_verified",
      repository_file_count: 2,
      levels: [
        {
          identifier: "lower_primary",
          name: "Lower Primary",
          official_phase: "Key Phase 2 (Basic 1–3)",
          scope_note: "Official scope statement for Lower Primary.",
          review_status: "not_verified",
        },
        {
          identifier: "upper_primary",
          name: "Upper Primary",
          official_phase: "Key Phase 3 (Basic 4–6)",
          scope_note: "Official scope statement for Upper Primary.",
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
        {
          identifier: "science",
          name: "Science",
          phase: "primary",
          availability: "present_unverified",
          review_status: "not_verified",
        },
        {
          identifier: "english",
          name: "English",
          phase: "primary",
          availability: "missing",
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
          status: "extracted",
          evidence_scope: "level",
          source_url: "https://nacca.gov.gh/curriculum/",
        },
        {
          level_identifier: "lower_primary",
          level_name: "Lower Primary",
          phase: "primary",
          subject_identifier: "science",
          subject_name: "Science",
          status: "located",
          evidence_scope: "level",
          source_url: "https://nacca.gov.gh/curriculum/",
        },
        {
          level_identifier: "upper_primary",
          level_name: "Upper Primary",
          phase: "primary",
          subject_identifier: "english",
          subject_name: "English",
          status: "missing",
          evidence_scope: "level",
          source_url: "https://nacca.gov.gh/curriculum/",
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
      levels: [
        {
          identifier: "lower_secondary",
          name: "O-Level (S1–S4)",
          official_phase: "UCE cycle",
          scope_note: "Official scope statement for Lower Secondary.",
          review_status: "not_verified",
        },
      ],
      subjects: [],
      coverage_matrix: [],
    },
  ],
} as const satisfies CurriculumCoverageReport;

describe("coverage panels", () => {
  it("shows a stable two-country skeleton while loading", () => {
    render(<CoveragePanels state={{ status: "loading" }} onRetry={vi.fn()} />);

    expect(screen.getByRole("heading", { level: 3, name: "Ghana" })).toBeVisible();
    expect(screen.getByRole("heading", { level: 3, name: "Uganda" })).toBeVisible();
    expect(screen.getAllByText("Checking public coverage evidence…")).toHaveLength(2);
  });

  it("shows exact declared evidence without phase-wide inference", async () => {
    const user = userEvent.setup();
    render(<CoveragePanels state={{ status: "loaded", report }} onRetry={vi.fn()} />);

    expect(screen.getByText("2 unreviewed subject records are visible")).toBeVisible();
    expect(screen.getByText("No public evidence is available yet")).toBeVisible();
    expect(screen.getAllByText("Lower Primary").length).toBeGreaterThan(0);
    await user.click(screen.getByText("View all 2 evidence subject records"));
    const evidenceSubjects = screen.getByRole("list", {
      name: "Ghana subjects found in public evidence",
    });
    expect(within(evidenceSubjects).getByText("Mathematics")).toBeVisible();
    expect(within(evidenceSubjects).getByText("Science")).toBeVisible();
    expect(within(evidenceSubjects).queryByText("English")).not.toBeInTheDocument();
    await user.click(screen.getByText("See level and subject evidence matrix"));
    expect(screen.getAllByText("exact level")).toHaveLength(3);
    expect(screen.getByText("1 extracted · 1 located · 1 explicitly missing")).toBeVisible();
    expect(screen.getAllByText("No educator review has been recorded.")).toHaveLength(2);
    await user.click(screen.getByText("See level and subject evidence matrix"));
  });

  it("does not infer a subject from unrelated repository files", () => {
    const noExactSubjectReport: CurriculumCoverageReport = {
      ...report,
      countries: [
        {
          ...report.countries[0],
          subjects: report.countries[0].subjects.map((subject) => ({
            ...subject,
            availability: "missing",
          })),
          coverage_matrix: [],
        },
      ],
    };
    render(
      <CoveragePanels
        state={{ status: "loaded", report: noExactSubjectReport }}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText("No exact subject record is available yet")).toBeVisible();
    expect(
      screen.getByText(
        "No subject records are currently visible in the public evidence catalogue.",
      ),
    ).toBeVisible();
    expect(
      screen.queryByRole("list", { name: "Ghana subjects found in public evidence" }),
    ).not.toBeInTheDocument();
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

  it("surfaces immutable release provenance and explicit review state", () => {
    render(<CoveragePanels state={{ status: "loaded", report }} onRetry={vi.fn()} />);

    const note = screen.getByRole("note", { name: "Evidence snapshot" });
    expect(note).toHaveTextContent("Catalogue checked 27 Jul 2026");
    expect(note).toHaveTextContent("Data release: curriculum-2026-07-29-candidate.1");
    expect(note).toHaveTextContent("No human review is recorded for this snapshot.");
  });

  it("handles unavailable release identity and reviewed evidence honestly", () => {
    const reviewedReport: CurriculumCoverageReport = {
      ...report,
      snapshot: {
        ...report.snapshot,
        source_version: null,
        review_status: "human_reviewed",
      },
      countries: [
        {
          ...report.countries[0],
          review_status: "human_reviewed",
          subjects: [report.countries[0].subjects[0]],
          coverage_matrix: [report.countries[0].coverage_matrix[0]],
        },
      ],
    };
    render(
      <CoveragePanels state={{ status: "loaded", report: reviewedReport }} onRetry={vi.fn()} />,
    );

    expect(screen.getByText("1 reviewed subject record is visible")).toBeVisible();
    expect(screen.getByText("Human review has been recorded.")).toBeVisible();
    const note = screen.getByRole("note", { name: "Evidence snapshot" });
    expect(note).toHaveTextContent("Data release identity is not available");
    expect(note).toHaveTextContent("Human review is recorded for this snapshot.");
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
