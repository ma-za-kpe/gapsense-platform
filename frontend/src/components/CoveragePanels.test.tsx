import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoveragePanels } from "./CoveragePanels";

const report = {
  repository_status: "available",
  complete: false,
  warnings: [],
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
    expect(screen.getAllByText("Checking local coverage evidence…")).toHaveLength(2);
  });

  it("renders file presence separately from unverified review", () => {
    render(<CoveragePanels state={{ status: "loaded", report }} onRetry={vi.fn()} />);

    expect(screen.getByText("1 repository file located")).toBeVisible();
    expect(screen.getByText("No canonical repository files located")).toBeVisible();
    expect(screen.getByText("Lower Primary")).toBeVisible();
    expect(screen.getAllByText("Extraction and educator review not verified")).toHaveLength(2);
  });

  it("explains the evidence-to-question organization for teachers", async () => {
    const user = userEvent.setup();
    render(<CoveragePanels state={{ status: "loaded", report }} onRetry={vi.fn()} />);

    const firstToggle = screen.getAllByText("See how questions are organised").at(0);
    if (firstToggle === undefined) {
      throw new Error("Ghana curriculum map toggle was not rendered");
    }
    await user.click(firstToggle);

    expect(screen.getByText("NaCCA standards-based structure")).toBeVisible();
    expect(screen.getByText("Content standard and indicator")).toBeVisible();
    expect(screen.getByRole("link", { name: /Open Ghana authority source/ })).toHaveAttribute(
      "href",
      "https://nacca.gov.gh/curriculum/",
    );
  });

  it("keeps country context visible and supports recovery when unavailable", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(<CoveragePanels state={{ status: "unavailable" }} onRetry={onRetry} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Live coverage details are unavailable");
    await user.click(screen.getByRole("button", { name: "Retry coverage details" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
