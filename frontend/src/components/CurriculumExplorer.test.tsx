import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CurriculumExplorer } from "./CurriculumExplorer";
import { getCurriculumDetail, type CurriculumDetail } from "../services/details";

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
    source_version: null,
    review_status: "not_verified",
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
          identifier: "lower_primary",
          name: "Lower Primary",
          official_phase: "Basic 1-3",
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
    },
  ],
} as const;

const detail: CurriculumDetail = {
  country: "Ghana",
  phase: "primary",
  level: "lower_primary",
  subject: "mathematics",
  evidence_scope: "phase_only",
  extraction_status: "extracted",
  source_files: ["standards.json"],
  strands: [{ identifier: "Number", name: "Number", sub_strands: ["Counting", "Operations"] }],
  nodes: [
    {
      code: "B1.Number.1",
      title: "Count objects",
      content_standard: "Count to 100",
      prerequisites: [],
      indicators: [
        { code: "I1", title: "", question_type: null, difficulty: null, misconception_count: 0 },
      ],
    },
  ],
};

describe("curriculum explorer", () => {
  it("lets users inspect the evidence tree and switch country", async () => {
    vi.mocked(getCurriculumDetail).mockResolvedValue(detail);
    const user = userEvent.setup();
    render(<CurriculumExplorer state={{ status: "loaded", report }} onRetry={vi.fn()} />);
    expect(screen.getByText(/Choose a country/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText(/1 standards/).length).toBeGreaterThan(0));
    expect(screen.getByText("Counting")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Level"), "lower_primary");
    await user.selectOptions(screen.getByLabelText("Subject"), "mathematics");
    await user.click(screen.getByLabelText("Country"));
    await user.selectOptions(screen.getByLabelText("Country"), "UG");
    expect(screen.getByRole("option", { name: "Lower Secondary" })).toBeInTheDocument();
    await waitFor(() =>
      expect(getCurriculumDetail).toHaveBeenCalledWith(expect.stringContaining("uganda/secondary")),
    );
  });

  it("shows unavailable detail without inventing content", async () => {
    vi.mocked(getCurriculumDetail).mockRejectedValue(new Error("not found"));
    render(<CurriculumExplorer state={{ status: "loaded", report }} onRetry={vi.fn()} />);
    await waitFor(() => expect(screen.getByText(/no safe extracted detail/)).toBeInTheDocument());
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
          content_standard: "",
          prerequisites: [],
          indicators: [],
        },
      ],
    });
    await waitFor(() => expect(screen.getByText(/Level evidence/)).toBeInTheDocument());
  });

  it("replaces an empty public catalogue with a useful non-interactive boundary", () => {
    const emptyReport = {
      ...report,
      countries: report.countries.map((country) => ({ ...country, levels: [], subjects: [] })),
    };
    render(
      <CurriculumExplorer state={{ status: "loaded", report: emptyReport }} onRetry={vi.fn()} />,
    );
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "No public subject evidence is available yet",
      }),
    ).toBeVisible();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Read how evidence is published" })).toHaveAttribute(
      "href",
      "/about#evidence",
    );
  });

  it("offers retry while coverage is not loaded", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(<CurriculumExplorer state={{ status: "loading" }} onRetry={onRetry} />);
    await user.click(screen.getByRole("button", { name: "Retry coverage details" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
