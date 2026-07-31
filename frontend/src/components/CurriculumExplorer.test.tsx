import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CurriculumExplorer } from "./CurriculumExplorer";
import {
  getCurriculumDetail,
  type CurriculumDetail,
  type CurriculumNode,
} from "../services/details";

vi.mock("../services/details", async () => {
  const actual = await vi.importActual<typeof import("../services/details")>("../services/details");
  return { ...actual, getCurriculumDetail: vi.fn() };
});

const report = {
  repository_status: "available",
  complete: false,
  warnings: [],
  snapshot: {
    generated_at: "2026-07-27T17:00:00Z",
    source_version: "curriculum-test-candidate.1",
    review_status: "not_verified",
  },
  catalog: {
    as_of: "2026-07-29",
    scope_status: "official_authority_inventory",
    represented_cells: 4,
    total_cells: 4,
    evidence_cells: 2,
  },
  source_inventory: {
    as_of: "2026-07-23",
    total_records: 2,
    acquired_artifacts: 1,
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
      {
        identifier: "ug-lower-secondary-mathematics",
        country: "UG",
        phase: "primary",
        level: "P1-P3",
        subject: "mathematics",
        edition: "2019",
        source_url: "https://ncdc.go.ug/resource/lower-secondary-mathematics/",
        retrieved_on: "2026-07-23",
        license_status: "all_rights_reserved_permission_required",
        artifact_available: true,
        artifact_pages: 48,
        extraction_status: "normalized_projection_unverified",
        review_status: "official_artifact_byte_verified",
        known_gap: "Structured extraction remains.",
      },
    ],
  },
  countries: [
    {
      code: "GH",
      name: "Ghana",
      authority: "NaCCA",
      authority_url: "https://nacca.gov.gh",
      availability: "present_unverified",
      review_status: "not_verified",
      repository_file_count: 1,
      levels: [
        {
          identifier: "kindergarten",
          name: "Kindergarten",
          official_phase: "Basic KG",
          scope_note: "OWOP remains a standalone Kindergarten learning area.",
          review_status: "not_verified",
        },
        {
          identifier: "lower_primary",
          name: "Lower Primary",
          official_phase: "Basic 1-3",
          scope_note: "OWOP is integrated into related subjects.",
          review_status: "not_verified",
        },
        {
          identifier: "upper_primary",
          name: "Upper Primary",
          official_phase: "Basic 4-6",
          scope_note: "OWOP is integrated into related subjects.",
          review_status: "not_verified",
        },
      ],
      subjects: [
        {
          identifier: "numeracy",
          name: "Numeracy",
          phase: "primary",
          availability: "missing",
          review_status: "not_verified",
        },
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
          availability: "missing",
          review_status: "not_verified",
        },
      ],
      coverage_matrix: [
        {
          level_identifier: "kindergarten",
          level_name: "Kindergarten",
          phase: "primary",
          subject_identifier: "numeracy",
          subject_name: "Numeracy",
          status: "missing",
          evidence_scope: "level",
          source_url: "https://nacca.gov.gh/curriculum/",
        },
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
          level_identifier: "upper_primary",
          level_name: "Upper Primary",
          phase: "primary",
          subject_identifier: "science",
          subject_name: "Science",
          status: "missing",
          evidence_scope: "level",
          source_url: "https://nacca.gov.gh/curriculum/",
        },
      ],
    },
    {
      code: "UG",
      name: "Uganda",
      authority: "NCDC",
      authority_url: "https://ncdc.go.ug",
      availability: "present_unverified",
      review_status: "not_verified",
      repository_file_count: 1,
      levels: [
        {
          identifier: "lower_secondary",
          name: "Lower Secondary",
          official_phase: "O level",
          scope_note: "This is the complete curriculum menu.",
          review_status: "not_verified",
        },
      ],
      subjects: [
        {
          identifier: "mathematics",
          name: "Mathematics",
          phase: "secondary",
          availability: "present_unverified",
          review_status: "not_verified",
        },
      ],
      coverage_matrix: [
        {
          level_identifier: "lower_secondary",
          level_name: "Lower Secondary",
          phase: "secondary",
          subject_identifier: "mathematics",
          subject_name: "Mathematics",
          status: "extracted",
          evidence_scope: "level",
          source_url: "https://ncdc.go.ug/directorates/",
        },
      ],
    },
  ],
} as const;

const assignedNode: CurriculumNode = {
  code: "B1.9.1",
  title: "Count objects",
  record_kind: "source_page",
  content_standard: "Count to 100",
  source_id: "gh-primary-mathematics",
  source_page: 42,
  curriculum_path: ["SEC.00000", "SEC.00001", "SEC.00002"],
  section_identifier: "SEC.00002",
  strand_identifier: "Number",
  prerequisite_status: "not_stated_by_authority",
  prerequisites: [],
  evidence_items: [
    { kind: "indicator", code: "B1.9.1.1", text: "Count objects to 100" },
    { kind: "learning_outcome", code: null, text: "Use counting in context" },
  ],
  indicators: [
    { code: "I1", title: "", question_type: null, difficulty: null, misconception_count: 0 },
  ],
};

const detail: CurriculumDetail = {
  release_id: "curriculum-test-candidate.1",
  country: "ghana",
  phase: "primary",
  level: "lower_primary",
  subject: "mathematics",
  evidence_scope: "level",
  extraction_status: "extracted",
  extraction_method: "lossless-page-and-native-heading-projection",
  source_files: ["standards.json"],
  curriculum_model: "ghana-standards-based",
  structure_status: "machine_extracted_not_human_verified",
  sections: [
    {
      identifier: "SEC.00000",
      parent_identifier: null,
      kind: "document",
      title: "Mathematics official curriculum",
      source_id: "gh-primary-mathematics",
      source_page: 1,
    },
    {
      identifier: "SEC.00001",
      parent_identifier: "SEC.00000",
      kind: "strand",
      title: "Number",
      source_id: "gh-primary-mathematics",
      source_page: 20,
    },
    {
      identifier: "SEC.00002",
      parent_identifier: "SEC.00001",
      kind: "sub_strand",
      title: "Counting",
      source_id: "gh-primary-mathematics",
      source_page: 42,
    },
  ],
  strands: [{ identifier: "Number", name: "Number", sub_strands: ["Counting", "Operations"] }],
  nodes: [
    assignedNode,
    {
      code: "B1.9.2",
      title: "Unassigned standard",
      record_kind: "curriculum_standard",
      content_standard: "",
      source_id: null,
      source_page: null,
      curriculum_path: [],
      section_identifier: null,
      strand_identifier: null,
      prerequisite_status: "not_extracted",
      prerequisites: [],
      evidence_items: [],
      indicators: [],
    },
  ],
};

describe("curriculum explorer", () => {
  it("lets users inspect the evidence tree and switch country", async () => {
    vi.mocked(getCurriculumDetail).mockResolvedValue(detail);
    const user = userEvent.setup();
    render(<CurriculumExplorer state={{ status: "loaded", report }} onRetry={vi.fn()} />);
    expect(screen.getByText(/Choose a country/)).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText(/Country-native curriculum model/)).toBeInTheDocument(),
    );
    expect(screen.getByText("Counting")).toBeInTheDocument();
    expect(screen.getByText("Unassigned standard")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Kindergarten" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Upper Primary" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "Every declared Ghana and Uganda curriculum area",
      }),
    ).toBeVisible();
    expect(screen.getByText(/4 of 4/)).toBeVisible();
    expect(screen.getByText("Numeracy")).toBeInTheDocument();
    expect(screen.getByText("Science")).toBeInTheDocument();
    expect(
      screen.getByText("OWOP remains a standalone Kindergarten learning area."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("OWOP is integrated into related subjects.")).toHaveLength(2);
    expect(screen.getAllByText("Missing data")).toHaveLength(2);
    const sourceInventoryHeading = screen.getByRole("heading", {
      level: 2,
      name: "Every release-qualified official source record",
    });
    expect(sourceInventoryHeading).toBeVisible();
    expect(sourceInventoryHeading.closest("section")).toHaveTextContent(
      "2 source records are accounted for",
    );
    expect(screen.getByText("Official index only")).toBeInTheDocument();
    expect(screen.getByText("Normalized projection, unverified")).toBeInTheDocument();
    expect(screen.getByText("Page count unavailable")).toBeInTheDocument();
    expect(screen.getByText("48 official pages")).toBeInTheDocument();
    expect(
      screen.getByText("Text extraction: Lossless Page And Native Heading Projection."),
    ).toBeInTheDocument();
    expect(screen.getByText("Primary · 2019")).toBeInTheDocument();
    expect(screen.getByText("Secondary · current index")).toBeInTheDocument();
    expect(screen.getByText("gh-jhs-official-index-current")).toBeInTheDocument();
    expect(screen.getAllByText("Retrieved 2026-07-23")).toHaveLength(2);
    expect(screen.getByText("Review: Official Index Verified")).toBeInTheDocument();
    expect(screen.getByText("Review: Official Artifact Byte Verified")).toBeInTheDocument();
    expect(
      screen.getByText("Rights: Official Index Only Document Not Licensed For Redistribution"),
    ).toBeInTheDocument();
    expect(screen.getByText("Rights: All Rights Reserved Permission Required")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Level"), "lower_primary");
    await user.selectOptions(screen.getByLabelText("Subject"), "mathematics");
    await user.click(screen.getByLabelText("Country"));
    await user.selectOptions(screen.getByLabelText("Country"), "UG");
    expect(screen.getByRole("option", { name: "Lower Secondary" })).toBeInTheDocument();
    await waitFor(() =>
      expect(getCurriculumDetail).toHaveBeenCalledWith(
        expect.stringContaining("uganda/secondary"),
        expect.any(AbortSignal),
      ),
    );
  });

  it("renders both populated and explicitly empty projected prerequisite relationships", async () => {
    vi.mocked(getCurriculumDetail).mockResolvedValue({
      ...detail,
      nodes: [
        {
          ...assignedNode,
          code: "B1.9.1.projected",
          title: "Projected prerequisite",
          prerequisite_status: "projected_relationships",
          prerequisites: ["B1.8.4", "B1.8.5"],
        },
        {
          ...assignedNode,
          code: "B1.9.2.projected",
          title: "Explicitly empty prerequisite set",
          prerequisite_status: "projected_relationships",
          prerequisites: [],
        },
      ],
    });

    render(<CurriculumExplorer state={{ status: "loaded", report }} onRetry={vi.fn()} />);

    expect(await screen.findByText("Projected prerequisite")).toBeInTheDocument();
    expect(screen.getByText(/B1\.8\.4, B1\.8\.5/)).toBeInTheDocument();
    expect(screen.getByText(/projected relationship set is explicitly empty/)).toBeInTheDocument();
  });

  it("shows unavailable detail without inventing content", async () => {
    vi.mocked(getCurriculumDetail).mockRejectedValue(new Error("not found"));
    render(<CurriculumExplorer state={{ status: "loaded", report }} onRetry={vi.fn()} />);
    await waitFor(() => expect(screen.getByText(/could not be loaded/)).toBeInTheDocument());
  });

  it.each([
    ["release", { release_id: "curriculum-other-candidate.1" }],
    ["country", { country: "uganda" }],
    ["phase", { phase: "secondary" }],
    ["level", { level: "upper_primary" }],
    ["subject", { subject: "science" }],
  ])("rejects detail whose %s identity does not match", async (_field, override) => {
    vi.mocked(getCurriculumDetail).mockResolvedValue({
      ...detail,
      ...override,
    });

    render(<CurriculumExplorer state={{ status: "loaded", report }} onRetry={vi.fn()} />);

    await waitFor(() => expect(screen.getByText(/could not be loaded/)).toBeInTheDocument());
    expect(screen.queryByText("Count objects")).not.toBeInTheDocument();
  });

  it("renders loading status and level evidence while a request is pending", async () => {
    let resolve: ((value: typeof detail) => void) | undefined;
    vi.mocked(getCurriculumDetail).mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    render(<CurriculumExplorer state={{ status: "loaded", report }} onRetry={vi.fn()} />);
    await waitFor(() =>
      expect(screen.getByText(/Loading the selected curriculum tree/)).toBeInTheDocument(),
    );
    resolve?.({
      ...detail,
      evidence_scope: "level",
      nodes: [
        {
          code: "X",
          title: "Number sense",
          record_kind: "source_page",
          content_standard: "",
          source_id: "gh-primary-mathematics",
          source_page: 1,
          curriculum_path: ["SEC.00000", "SEC.00001", "SEC.00002"],
          section_identifier: "SEC.00002",
          strand_identifier: "Number",
          prerequisite_status: "not_stated_by_authority",
          prerequisites: [],
          evidence_items: [],
          indicators: [],
        },
      ],
    });
    await waitFor(() => expect(screen.getByText(/Level evidence/)).toBeInTheDocument());
  });

  it("does not let a stale country response overwrite the latest selection", async () => {
    let resolveGhana: ((value: CurriculumDetail) => void) | undefined;
    vi.mocked(getCurriculumDetail)
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveGhana = resolve;
          }),
      )
      .mockResolvedValueOnce({
        ...detail,
        country: "uganda",
        phase: "secondary",
        level: "lower_secondary",
        nodes: [{ ...assignedNode, title: "Uganda latest" }],
      });
    const user = userEvent.setup();
    render(<CurriculumExplorer state={{ status: "loaded", report }} onRetry={vi.fn()} />);

    await user.selectOptions(screen.getByLabelText("Country"), "UG");
    await screen.findByText("Uganda latest");
    resolveGhana?.({
      ...detail,
      nodes: [{ ...assignedNode, title: "Stale Ghana" }],
    });

    await waitFor(() => expect(screen.queryByText("Stale Ghana")).not.toBeInTheDocument());
    expect(screen.getByText("Uganda latest")).toBeInTheDocument();
  });

  it("ignores a stale rejected request and an aborted loading update", async () => {
    let rejectGhana: ((reason?: unknown) => void) | undefined;
    vi.mocked(getCurriculumDetail)
      .mockImplementationOnce(
        () =>
          new Promise((_, reject) => {
            rejectGhana = reject;
          }),
      )
      .mockResolvedValueOnce({
        ...detail,
        country: "uganda",
        phase: "secondary",
        level: "lower_secondary",
        nodes: [{ ...assignedNode, title: "Uganda retained" }],
      });
    const user = userEvent.setup();
    const rendered = render(
      <CurriculumExplorer state={{ status: "loaded", report }} onRetry={vi.fn()} />,
    );

    await user.selectOptions(screen.getByLabelText("Country"), "UG");
    await screen.findByText("Uganda retained");
    rejectGhana?.(new Error("stale request"));
    await waitFor(() => expect(screen.getByText("Uganda retained")).toBeInTheDocument());

    vi.mocked(getCurriculumDetail).mockReturnValueOnce(new Promise(() => undefined));
    rendered.unmount();
    const remounted = render(
      <CurriculumExplorer state={{ status: "loaded", report }} onRetry={vi.fn()} />,
    );
    remounted.unmount();
    await Promise.resolve();
  });

  it("keeps every catalogue selector available when no safe detail projection exists", async () => {
    const emptyReport = {
      ...report,
      catalog: { ...report.catalog, evidence_cells: 0 },
      countries: report.countries.map((country) => ({
        ...country,
        availability: "missing" as const,
        subjects: country.subjects.map((subject) => ({
          ...subject,
          availability: "missing" as const,
        })),
        coverage_matrix: country.coverage_matrix.map((entry) => ({
          ...entry,
          status: "missing" as const,
        })),
      })),
    };
    render(
      <CurriculumExplorer state={{ status: "loaded", report: emptyReport }} onRetry={vi.fn()} />,
    );
    const user = userEvent.setup();
    expect(screen.getAllByRole("combobox")).toHaveLength(3);
    expect(screen.getByLabelText("Country")).toHaveValue("GH");
    expect(screen.getByLabelText("Level")).toHaveValue("kindergarten");
    expect(screen.getByLabelText("Subject")).toHaveValue("numeracy");
    await user.selectOptions(screen.getByLabelText("Level"), "upper_primary");
    await user.selectOptions(screen.getByLabelText("Subject"), "science");
    expect(screen.getByLabelText("Subject")).toHaveValue("science");
    await user.selectOptions(screen.getByLabelText("Country"), "UG");
    expect(screen.getByLabelText("Country")).toHaveValue("UG");
    expect(screen.getByLabelText("Level")).toHaveValue("lower_secondary");
    expect(screen.getByLabelText("Subject")).toHaveValue("mathematics");
    expect(screen.getByText(/release-qualified detail is unavailable/)).toBeVisible();
    expect(screen.getByText(/4 of 4/)).toBeVisible();
    expect(screen.getByText(/4 remain explicit data gaps/)).toBeVisible();
  });

  it("explains an authority-located curriculum cell without calling it missing", async () => {
    const locatedReport = {
      ...report,
      catalog: { ...report.catalog, evidence_cells: 3 },
      countries: report.countries.map((country) =>
        country.code === "GH"
          ? {
              ...country,
              coverage_matrix: country.coverage_matrix.map((entry) =>
                entry.subject_identifier === "numeracy"
                  ? { ...entry, status: "located" as const }
                  : entry,
              ),
            }
          : country,
      ),
    };
    vi.mocked(getCurriculumDetail).mockResolvedValue({
      ...detail,
      level: "kindergarten",
      subject: "numeracy",
      extraction_status: "located",
      extraction_method: "not_available",
      source_files: [],
      curriculum_model: "official-catalogue-entry",
      structure_status: "source_artifact_not_available",
      sections: [],
      strands: [],
      nodes: [],
    });

    render(
      <CurriculumExplorer state={{ status: "loaded", report: locatedReport }} onRetry={vi.fn()} />,
    );

    expect(
      await screen.findByText(
        /authority does not currently expose a downloadable subject syllabus/,
      ),
    ).toBeVisible();
    expect(
      screen.getByRole("heading", { level: 2, name: "Numeracy is represented" }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "View the official authority inventory" }),
    ).toHaveAttribute("href", "https://nacca.gov.gh");
  });

  it("shows fail-closed catalogue and source boundaries for an unavailable release", () => {
    const unavailableReport = {
      ...report,
      repository_status: "missing" as const,
      catalog: null,
      source_inventory: null,
      snapshot: { ...report.snapshot, source_version: null },
      countries: report.countries.map((country) => ({
        ...country,
        availability: "missing" as const,
        subjects: [],
        coverage_matrix: [],
      })),
    };

    render(
      <CurriculumExplorer
        state={{ status: "loaded", report: unavailableReport }}
        onRetry={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("heading", { level: 2, name: "Whole curriculum catalogue unavailable" }),
    ).toBeVisible();
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "Data project source inventory unavailable",
      }),
    ).toBeVisible();
  });

  it("offers retry while coverage is not loaded", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(<CurriculumExplorer state={{ status: "loading" }} onRetry={onRetry} />);
    await user.click(screen.getByRole("button", { name: "Retry coverage details" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
