import axe from "axe-core";
import { StrictMode } from "react";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { saveSampleDraft } from "./domain/sampleDraft";
import type { AnalyticsEventName } from "./analytics/client";

const readyResponse = () =>
  new Response(JSON.stringify({ status: "ready", checks: { curriculum_repository: "ok" } }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });

const country = (code: "GH" | "UG", withSubject: boolean) => ({
  code,
  name: code === "GH" ? "Ghana" : "Uganda",
  authority:
    code === "GH"
      ? "National Council for Curriculum and Assessment (NaCCA)"
      : "National Curriculum Development Centre (NCDC)",
  authority_url:
    code === "GH" ? "https://nacca.gov.gh/curriculum/" : "https://ncdc.go.ug/directorates/",
  availability: withSubject ? "present_unverified" : "missing",
  review_status: "not_verified",
  repository_file_count: withSubject ? 2 : 0,
  levels: [
    {
      identifier: code === "GH" ? "lower_primary" : "primary_1_3",
      name: code === "GH" ? "Lower Primary" : "Primary One–Three",
      official_phase: code === "GH" ? "Key Phase 2" : "Primary Phase 1",
      scope_note: "Official scope statement.",
      review_status: "not_verified",
    },
  ],
  subjects: [
    {
      identifier: "mathematics",
      name: "Mathematics",
      phase: "primary",
      availability: withSubject ? "present_unverified" : "missing",
      review_status: "not_verified",
    },
  ],
  coverage_matrix: [
    {
      level_identifier: code === "GH" ? "lower_primary" : "primary_1_3",
      level_name: code === "GH" ? "Lower Primary" : "Primary One–Three",
      phase: "primary",
      subject_identifier: "mathematics",
      subject_name: "Mathematics",
      status: withSubject ? "extracted" : "missing",
      evidence_scope: "level",
      source_url:
        code === "GH" ? "https://nacca.gov.gh/curriculum/" : "https://ncdc.go.ug/directorates/",
    },
  ],
});

const coveragePayload = (withSubjects = true) => ({
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
    represented_cells: 2,
    total_cells: 2,
    evidence_cells: withSubjects ? 2 : 0,
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
        phase: "secondary",
        level: "S1-S4",
        subject: "mathematics",
        edition: "2019",
        source_url: "https://ncdc.go.ug/resource/lower-secondary-mathematics/",
        retrieved_on: "2026-07-23",
        license_status: "all_rights_reserved_permission_required",
        artifact_available: true,
        artifact_pages: 48,
        extraction_status: "not_extracted",
        review_status: "official_artifact_byte_verified",
        known_gap: "Structured extraction remains.",
      },
    ],
  },
  countries: [country("GH", withSubjects), country("UG", withSubjects)],
});

const detailPayload = {
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
  ],
  strands: [{ identifier: "Number", name: "Number", sub_strands: ["Counting"] }],
  nodes: [
    {
      code: "B1.Number.1",
      title: "Count objects",
      record_kind: "source_page",
      content_standard: "Count to 100",
      source_id: "gh-primary-mathematics",
      source_page: 42,
      curriculum_path: ["SEC.00000"],
      section_identifier: "SEC.00000",
      strand_identifier: "Number",
      prerequisite_status: "not_stated_by_authority",
      prerequisites: [],
      evidence_items: [],
      indicators: [],
    },
  ],
};

const requestUrl = (input: RequestInfo | URL): string =>
  typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

const stubReadyApi = (withSubjects = true) => {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>().mockImplementation((input) => {
      const url = requestUrl(input);
      if (url.includes("/curriculum/coverage")) {
        return Promise.resolve(
          new Response(JSON.stringify(coveragePayload(withSubjects)), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      if (url.includes("/curriculum/")) {
        return Promise.resolve(
          new Response(JSON.stringify(detailPayload), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      return Promise.resolve(readyResponse());
    }),
  );
};

const settleBackgroundRequests = async () => {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
};

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
  window.history.pushState({}, "", "/");
});

describe("truthful public GapSense experience", () => {
  it("states the mission and keeps the illustrative product model separate from current evidence", async () => {
    stubReadyApi();
    const { container } = render(<App />);

    expect(container.querySelector(".site-header__inner")).toHaveClass("section-shell");
    expect(screen.getByRole("group", { name: "Theme" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 1, name: "Find the next learning step." }),
    ).toBeVisible();
    expect(screen.getByText("Find the gap. See the reason. Take the next step.")).toBeVisible();
    expect(
      screen.getByText(/help educators identify the earliest learning prerequisite/i),
    ).toBeVisible();

    const model = screen.getByRole("figure", { name: "Illustrative learning path" });
    expect(within(model).getByText("Fractions")).toBeVisible();
    expect(within(model).getByText("Equal groups")).toBeVisible();
    expect(within(model).getByText("Counting")).toBeVisible();
    expect(within(model).getByText("Visual grouping practice")).toBeVisible();
    const modelNote = within(model).getByText(
      "Example only — not a learner diagnosis or a claim about current curriculum coverage.",
    );
    expect(modelNote).toBeVisible();
    expect(modelNote.tagName).toBe("FIGCAPTION");
    expect(modelNote.parentElement).toBe(model);
    expect(within(model).getByText("Product model")).toBeVisible();
    expect(model).not.toHaveTextContent(/92|confidence/i);

    expect(
      screen.getByText(/Today, the public release offers clearly labelled activity samples/i),
    ).toBeVisible();
    expect(container).not.toHaveTextContent(/local evidence mount|Ollama/i);
    expect(await screen.findByText("Public evidence catalogue connected")).toBeVisible();
    expect(
      (await screen.findAllByText("1 unreviewed subject record is visible")).length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Curriculum" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "About" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Evidence" })).toHaveAttribute("href", "/evidence");
    expect(screen.getByRole("link", { name: "Privacy" })).toHaveAttribute("href", "/privacy");
    expect(screen.getByRole("link", { name: "Terms" })).toHaveAttribute("href", "/terms");
    expect(screen.getByRole("link", { name: "Accessibility" })).toHaveAttribute(
      "href",
      "/about#accessibility",
    );
  });

  it("renders a real curriculum tree only when public subject evidence exists", async () => {
    window.history.pushState({}, "", "/curriculum");
    stubReadyApi();
    const { container } = render(<App />);

    expect(container.querySelector(".page-shell--curriculum")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 1, name: "Inspect the public evidence boundary." }),
    ).toBeVisible();
    expect(await screen.findByRole("combobox", { name: "Subject" })).toHaveValue("mathematics");
    expect(await screen.findByText(/Country-native curriculum model/)).toBeVisible();
    expect(
      screen.getByText(/1 traced structural sections index 1 complete source pages/),
    ).toBeVisible();
  });

  it("keeps complete curriculum controls usable while showing an explicit evidence boundary", async () => {
    window.history.pushState({}, "", "/curriculum");
    stubReadyApi(false);
    render(<App />);

    expect(await screen.findByRole("combobox", { name: "Country" })).toHaveValue("GH");
    expect(screen.getByRole("combobox", { name: "Level" })).toHaveValue("lower_primary");
    expect(screen.getByRole("combobox", { name: "Subject" })).toHaveValue("mathematics");
    expect(await screen.findByText(/release-qualified detail is unavailable/)).toBeVisible();
    expect(screen.getByText(/Every declared combination is selectable/)).toBeVisible();
    expect(screen.getByText(/2 of 2/)).toBeVisible();
  });

  it("opens and reloads a focused assessment route from a persisted choice", async () => {
    stubReadyApi(false);
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("radio", { name: /^Teacher/ }));
    await user.click(screen.getByRole("radio", { name: /^Ghana/ }));
    await user.click(screen.getByRole("radio", { name: /^Practice activity/ }));
    await user.click(screen.getByRole("button", { name: "Review sample choice" }));
    await user.click(screen.getByRole("button", { name: "Open sample activity" }));

    expect(window.location.pathname).toBe("/assessment");
    expect(
      screen.getByRole("heading", { level: 1, name: "Ghana Basic 3 Science sample" }),
    ).toBeVisible();

    const current = screen.getByRole("heading", {
      level: 1,
      name: "Ghana Basic 3 Science sample",
    });
    expect(current).toBeVisible();
  });

  it("offers recovery when the assessment route has no reviewed draft", async () => {
    window.history.pushState({}, "", "/assessment");
    stubReadyApi(false);
    render(<App />);
    await settleBackgroundRequests();

    expect(
      screen.getByRole("heading", { level: 1, name: "No saved sample activity" }),
    ).toBeVisible();
  });

  it("returns from an empty assessment route to the sample chooser", async () => {
    window.history.pushState({}, "", "/assessment");
    stubReadyApi(false);
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Choose a sample" }));

    expect(window.location.pathname).toBe("/");
    expect(
      screen.getByRole("heading", { level: 1, name: "Find the next learning step." }),
    ).toBeVisible();
  });

  it("provides public trust, privacy, accessibility, evidence, and feedback information", async () => {
    window.history.pushState({}, "", "/about");
    stubReadyApi(false);
    const { container } = render(<App />);
    await settleBackgroundRequests();

    expect(
      screen.getByRole("heading", { level: 1, name: "How GapSense earns trust." }),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Evidence and review" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Privacy and saved choices" })).toBeVisible();
    expect(
      screen.getByText(
        /sample stores only the role, country context, and available purpose; the appearance control stores only your theme preference/i,
      ),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Accessibility commitment" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Feedback and correction" })).toBeVisible();
    expect(container).not.toHaveTextContent(/UNICEF/i);
  });

  it.each([
    ["/evidence", "Evidence, limitations, and known blockers.", "Known issues and blockers"],
    ["/privacy", "Privacy without surveillance.", "Browser storage"],
    ["/terms", "Use GapSense with evidence and care.", "Acceptable use"],
  ])("publishes the complete professional trust page at %s", async (path, title, section) => {
    window.history.pushState({}, "", path);
    stubReadyApi(false);
    render(<App />);
    await settleBackgroundRequests();

    expect(screen.getByRole("heading", { level: 1, name: title })).toBeVisible();
    expect(screen.getByRole("heading", { name: section })).toBeVisible();
    expect(
      screen.getByRole("navigation", { name: /page contents|policy contents|terms/i }),
    ).toBeVisible();
  });

  it.each([
    ["/", "GapSense — Find the next learning step"],
    ["/curriculum", "Curriculum evidence — GapSense"],
    ["/assessment", "Activity sample — GapSense"],
    ["/about", "Trust and evidence — GapSense"],
    ["/about/", "Trust and evidence — GapSense"],
    ["/evidence", "Evidence and limitations — GapSense"],
    ["/privacy", "Privacy policy — GapSense"],
    ["/terms", "Terms of use — GapSense"],
  ])("publishes distinct route metadata on %s", async (path, expectedTitle) => {
    window.history.pushState({}, "", path);
    stubReadyApi(false);
    render(<App />);
    await settleBackgroundRequests();

    expect(document.title).toBe(expectedTitle);
    expect(document.querySelector('meta[name="description"]')).toHaveAttribute(
      "content",
      expect.stringMatching(/evidence|sample|privacy/i),
    );
  });

  it("renders a recoverable not-found page for unsupported routes", async () => {
    window.history.pushState({}, "", "/missing");
    stubReadyApi(false);
    const { container } = render(<App />);
    await settleBackgroundRequests();

    expect(container.querySelector(".page-shell--not-found")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 1, name: "This page is not available" }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Return to GapSense" })).toHaveAttribute("href", "/");
  });

  it("responds to browser history navigation without a reload", async () => {
    stubReadyApi(false);
    render(<App />);
    await settleBackgroundRequests();

    act(() => {
      window.history.pushState({}, "", "/about");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    expect(
      await screen.findByRole("heading", { level: 1, name: "How GapSense earns trust." }),
    ).toBeVisible();
  });

  it("keeps the sample usable and makes API recovery explicit", async () => {
    const attempts = { coverage: 0, readiness: 0 };
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockImplementation((input) => {
        if (requestUrl(input).includes("/curriculum/coverage")) {
          attempts.coverage += 1;
          return attempts.coverage === 1
            ? Promise.reject(new TypeError("offline"))
            : Promise.resolve(
                new Response(JSON.stringify(coveragePayload(false)), {
                  status: 200,
                  headers: { "Content-Type": "application/json" },
                }),
              );
        }
        attempts.readiness += 1;
        return attempts.readiness === 1
          ? Promise.reject(new TypeError("offline"))
          : Promise.resolve(readyResponse());
      }),
    );
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText("Sample activity still works on this device")).toBeVisible();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Public coverage details are unavailable",
    );
    await user.click(screen.getByRole("button", { name: "Check connection again" }));
    await user.click(screen.getByRole("button", { name: "Retry coverage details" }));
    expect(await screen.findByText("Public evidence catalogue connected")).toBeVisible();
    expect(
      (await screen.findAllByText("No public evidence is available yet")).length,
    ).toBeGreaterThan(0);
  });

  it("records one anonymous entry event through StrictMode", async () => {
    stubReadyApi(false);
    const events: AnalyticsEventName[] = [];
    render(
      <StrictMode>
        <App analytics={{ track: (event) => events.push(event) }} />
      </StrictMode>,
    );

    await waitFor(() => expect(events).toEqual(["entry_viewed"]));
  });

  it.each(["/", "/curriculum", "/about", "/evidence", "/privacy", "/terms", "/assessment"])(
    "has no automatically detectable accessibility violation on %s",
    async (path) => {
      window.history.pushState({}, "", path);
      if (path === "/assessment") {
        saveSampleDraft(window.localStorage, {
          role: "teacher",
          country: "ghana",
          goal: "practice",
          reviewed: true,
        });
      }
      stubReadyApi(false);
      const { container } = render(<App />);
      await waitFor(() =>
        expect(screen.queryByText(/Checking public evidence/)).not.toBeInTheDocument(),
      );
      if (path === "/curriculum") {
        expect(await screen.findByText(/release-qualified detail is unavailable/)).toBeVisible();
      }

      const results = await axe.run(container, {
        runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"] },
      });
      expect(results.violations).toEqual([]);
    },
  );
});
