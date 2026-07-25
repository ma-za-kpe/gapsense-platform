import axe from "axe-core";
import { StrictMode } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { curriculumApiPath } from "./domain/curriculumPath";
import type { Analytics, AnalyticsEventName } from "./analytics/client";

const readyResponse = () =>
  new Response(JSON.stringify({ status: "ready", checks: { curriculum_repository: "ok" } }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });

const coveragePayload = {
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
      repository_file_count: 74,
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
      availability: "present_unverified",
      review_status: "not_verified",
      repository_file_count: 23,
      levels: [
        {
          identifier: "primary_1_3",
          name: "Primary One–Three",
          official_phase: "Primary Phase 1",
          review_status: "not_verified",
        },
      ],
    },
  ],
} as const;

const coverageResponse = () =>
  new Response(JSON.stringify(coveragePayload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });

const detailResponsePayload = () => ({
  country: "ghana",
  phase: "primary",
  level: "lower_primary",
  subject: "science",
  evidence_scope: "phase_only",
  extraction_status: "extracted",
  source_files: ["graph.json"],
  strands: [{ identifier: "1", name: "Number", sub_strands: ["Whole numbers"] }],
  nodes: [
    {
      code: "N1",
      title: "Counting",
      content_standard: "CS1",
      prerequisites: ["N0"],
      indicators: [
        {
          code: "I1",
          title: "Count",
          question_type: "oral",
          difficulty: 1,
          misconception_count: 0,
        },
      ],
    },
    { code: "N2", title: "Unmapped", content_standard: "", prerequisites: [], indicators: [] },
  ],
});

const detailResponse = () =>
  new Response(JSON.stringify(detailResponsePayload()), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });

const requestUrl = (input: RequestInfo | URL): string =>
  typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

const renderReadyApp = (analytics?: Analytics) => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockImplementation((input) =>
        Promise.resolve(
          requestUrl(input).includes("/curriculum/coverage")
            ? coverageResponse()
            : requestUrl(input).includes("/curriculum/ghana/")
              ? detailResponse()
              : readyResponse(),
        ),
      ),
  );
  return render(analytics === undefined ? <App /> : <App analytics={analytics} />);
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("GapSense web entry experience", () => {
  it("maps every country phase and subject to a bounded curriculum endpoint", () => {
    expect(curriculumApiPath("ghana", "Basic 1", "Mathematics")).toContain(
      "/primary/lower_primary/mathematics",
    );
    expect(curriculumApiPath("ghana", "Basic 4", "English Language")).toContain(
      "/primary/upper_primary/english",
    );
    expect(curriculumApiPath("ghana", "JHS (Basic 7â€“9)", "General Science")).toContain(
      "/secondary/junior_high/general_science",
    );
    expect(curriculumApiPath("ghana", "SHS", "Science")).toContain(
      "/secondary/senior_high/science",
    );
    expect(curriculumApiPath("uganda", "Primary 1", "Mathematics")).toContain(
      "/primary/primary_1_3/mathematics",
    );
    expect(curriculumApiPath("uganda", "Primary 4", "Mathematics")).toContain(
      "/primary/primary_4_7/mathematics",
    );
    expect(curriculumApiPath("uganda", "O-Level (S1â€“S4)", "Mathematics")).toContain(
      "/secondary/lower_secondary/mathematics",
    );
    expect(curriculumApiPath("uganda", "A-Level (S5â€“S6)", "Mathematics")).toContain(
      "/secondary/upper_secondary/mathematics",
    );
  });

  it("introduces both countries and reports connected local evidence", async () => {
    renderReadyApp();

    expect(
      screen.getByRole("heading", { level: 1, name: "Find the next learning step." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Ghana" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Uganda" })).toBeInTheDocument();
    expect(screen.getByText("No account. No learner data. No hidden AI dependency.")).toBeVisible();
    expect(await screen.findByText("Curriculum evidence connected")).toBeVisible();
    expect(await screen.findByText("74 repository files located")).toBeVisible();
    expect(screen.getByText("23 repository files located")).toBeVisible();
    expect(screen.getByRole("link", { name: "Curriculum" })).toHaveAttribute("href", "#curriculum");
    expect(
      screen.getByRole("heading", { level: 2, name: "Everything useful is one click away." }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: /Inspect curriculum evidence/ })).toHaveAttribute(
      "href",
      "#curriculum",
    );
    expect(screen.getByRole("heading", { level: 2, name: /See what is located/ })).toBeVisible();
  });

  it("uses Maku's Africa-first attribution without institutional branding", async () => {
    const { container } = renderReadyApp();

    expect(await screen.findByText("Curriculum evidence connected")).toBeVisible();
    expect(screen.getAllByRole("link", { name: "Maku" })).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: "Maku" })[0]).toHaveAttribute(
      "href",
      "https://startuptribunal.com/maku",
    );
    expect(screen.getByRole("link", { name: /Latest version/ })).toHaveAttribute(
      "href",
      "https://github.com/ma-za-kpe/gapsense-platform/releases",
    );
    expect(container).not.toHaveTextContent(/UNICEF/i);
  });

  it("keeps planning available when the API is unavailable and recovers on retry", async () => {
    const user = userEvent.setup();
    const analyticsEvents: AnalyticsEventName[] = [];
    const attempts = { coverage: 0, readiness: 0 };
    const fetcher = vi.fn<typeof fetch>().mockImplementation((input) => {
      if (requestUrl(input).includes("/curriculum/coverage")) {
        attempts.coverage += 1;
        if (attempts.coverage === 1) {
          return Promise.reject(new TypeError("offline"));
        }
        return Promise.resolve(coverageResponse());
      }
      attempts.readiness += 1;
      if (attempts.readiness === 1) {
        return Promise.reject(new TypeError("offline"));
      }
      return Promise.resolve(readyResponse());
    });
    vi.stubGlobal("fetch", fetcher);
    render(
      <App
        analytics={{
          track: (event) => {
            analyticsEvents.push(event);
          },
        }}
      />,
    );

    expect(await screen.findByText("Planning still works locally")).toBeVisible();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Live coverage details are unavailable",
    );
    const retry = screen.getByRole("button", { name: "Check connection again" });
    await user.click(retry);
    await user.click(screen.getByRole("button", { name: "Retry coverage details" }));

    expect(await screen.findByText("Curriculum evidence connected")).toBeVisible();
    expect(await screen.findByText("74 repository files located")).toBeVisible();
    expect(fetcher).toHaveBeenCalledTimes(4);
    expect(analyticsEvents).toEqual([
      "entry_viewed",
      "readiness_retry_selected",
      "coverage_retry_selected",
    ]);
  });

  it("builds and resets an honest Ghana starting point", async () => {
    const user = userEvent.setup();
    renderReadyApp();

    const reviewButton = screen.getByRole("button", { name: "Review my starting point" });
    expect(reviewButton).toBeDisabled();

    await user.click(screen.getByRole("radio", { name: /^Teacher/ }));
    await user.click(screen.getByRole("radio", { name: /^Ghana/ }));
    await user.click(screen.getByRole("radio", { name: /^Diagnostic check/ }));
    expect(reviewButton).toBeEnabled();
    await user.click(reviewButton);

    expect(
      screen.getByRole("heading", { level: 3, name: "Your Ghana starting point is ready" }),
    ).toBeVisible();
    expect(screen.getByText("Teacher · Diagnostic check")).toBeVisible();
    expect(screen.getByText(/NaCCA curriculum inventory is still being verified/)).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Start again" }));
    expect(screen.queryByText("Your Ghana starting point is ready")).not.toBeInTheDocument();
    expect(reviewButton).toBeDisabled();
  });

  it("uses Uganda-specific terminology in the reviewed plan", async () => {
    const user = userEvent.setup();
    renderReadyApp();

    await user.click(screen.getByRole("radio", { name: /^Parent or caregiver/ }));
    await user.click(screen.getByRole("radio", { name: /^Uganda/ }));
    await user.click(screen.getByRole("radio", { name: /^Practice activity/ }));
    await user.click(screen.getByRole("button", { name: "Review my starting point" }));

    expect(
      screen.getByRole("heading", { level: 3, name: "Your Uganda starting point is ready" }),
    ).toBeVisible();
    expect(screen.getByText("Parent or caregiver · Practice activity")).toBeVisible();
    expect(screen.getByText(/NCDC curriculum inventory is still being verified/)).toBeVisible();
  });

  it("keeps Uganda O-Level and A-Level available in the local web planner", async () => {
    const user = userEvent.setup();
    renderReadyApp();

    await user.click(screen.getByRole("radio", { name: /^Teacher/ }));
    await user.click(screen.getByRole("radio", { name: /^Uganda/ }));
    await user.click(screen.getByRole("radio", { name: /^Practice activity/ }));
    await user.click(screen.getByRole("button", { name: "Review my starting point" }));

    await user.selectOptions(screen.getByLabelText("Level"), "O-Level (S1–S4)");
    await user.click(screen.getByRole("button", { name: /Generate starter activity/ }));

    expect(screen.getByText(/Local draft · O-Level \(S1–S4\)/)).toBeVisible();
    expect(
      screen.getByRole("heading", { level: 4, name: "Mathematics Practice activity" }),
    ).toBeVisible();
  });

  it("generates and prints a local starter activity after reviewing intent", async () => {
    const user = userEvent.setup();
    renderReadyApp();
    await user.click(screen.getByRole("radio", { name: /^Teacher/ }));
    await user.click(screen.getByRole("radio", { name: /^Ghana/ }));
    await user.click(screen.getByRole("radio", { name: /^Practice activity/ }));
    await user.click(screen.getByRole("button", { name: "Review my starting point" }));

    await user.selectOptions(screen.getByLabelText("Level"), "Basic 3");
    await user.selectOptions(screen.getByLabelText("Subject"), "Science");
    await user.click(screen.getByRole("button", { name: /Generate starter activity/ }));

    expect(
      screen.getByRole("heading", { level: 4, name: "Science Practice activity" }),
    ).toBeVisible();
    expect(screen.getByText("Name one source of light.")).toBeVisible();
    const traceButton = screen.getAllByRole("button", { name: "Trace curriculum" })[0];
    if (traceButton === undefined) throw new Error("trace button missing");
    await user.click(traceButton);
    expect(await screen.findByText("Curriculum lineage")).toBeVisible();
    expect(await screen.findByText("Strands: Number")).toBeVisible();
    expect(screen.getByText(/Content standard: CS1/)).toBeVisible();
    const createObjectURL = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:assessment");
    const revokeObjectURL = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    await user.click(screen.getByRole("button", { name: "Download document" }));
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:assessment");
    click.mockRestore();
    createObjectURL.mockRestore();
    revokeObjectURL.mockRestore();
    const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
    await user.click(screen.getByRole("button", { name: "Print / save PDF" }));
    expect(print).toHaveBeenCalledOnce();
    print.mockRestore();
    const share = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "share", { configurable: true, value: share });
    await user.click(screen.getByRole("button", { name: "Share" }));
    expect(share).toHaveBeenCalledOnce();
    expect(await screen.findByRole("status")).toHaveTextContent("Share sheet opened");
    Reflect.deleteProperty(navigator, "share");
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    await user.click(screen.getByRole("button", { name: "Share" }));
    expect(writeText).toHaveBeenCalledOnce();
    expect(await screen.findByRole("status")).toHaveTextContent("copied to your clipboard");
    Reflect.deleteProperty(navigator, "clipboard");
    const shareRejected = vi.fn().mockRejectedValue(new Error("share dismissed"));
    Object.defineProperty(navigator, "share", { configurable: true, value: shareRejected });
    await user.click(screen.getByRole("button", { name: "Share" }));
    await waitFor(() => expect(shareRejected).toHaveBeenCalledOnce());
    Reflect.deleteProperty(navigator, "share");
    const writeRejected = vi.fn().mockRejectedValue(new Error("clipboard denied"));
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: writeRejected },
    });
    await user.click(screen.getByRole("button", { name: "Share" }));
    await waitFor(() => expect(writeRejected).toHaveBeenCalledOnce());
    Reflect.deleteProperty(navigator, "clipboard");
    await user.click(screen.getByRole("button", { name: "Share" }));
    await user.click(screen.getByText("Show answer guidance"));
    expect(screen.getByText("liquid")).toBeVisible();
  });

  it("fails closed when curriculum lineage is unavailable", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockImplementation((input) => {
        const url = requestUrl(input);
        if (url.includes("/curriculum/coverage")) return Promise.resolve(coverageResponse());
        if (url.includes("/curriculum/ghana/"))
          return Promise.resolve(new Response("", { status: 404 }));
        return Promise.resolve(readyResponse());
      }),
    );
    render(<App />);
    await user.click(screen.getByRole("radio", { name: /^Teacher/ }));
    await user.click(screen.getByRole("radio", { name: /^Ghana/ }));
    await user.click(screen.getByRole("radio", { name: /^Practice activity/ }));
    await user.click(screen.getByRole("button", { name: "Review my starting point" }));
    await user.click(screen.getByRole("button", { name: /Generate starter activity/ }));
    const traceButton = screen.getAllByRole("button", { name: "Trace curriculum" })[0];
    if (traceButton === undefined) throw new Error("trace button missing");
    await user.click(traceButton);
    expect(
      await screen.findByText("Lineage evidence is not available for this selection yet."),
    ).toBeVisible();
  });

  it("renders an honest empty lineage without inventing standards", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockImplementation((input) => {
        const url = requestUrl(input);
        if (url.includes("/curriculum/coverage")) return Promise.resolve(coverageResponse());
        if (url.includes("/curriculum/ghana/")) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                ...detailResponsePayload(),
                evidence_scope: "level",
                source_files: [],
                strands: [],
                nodes: [],
              }),
              { status: 200 },
            ),
          );
        }
        return Promise.resolve(readyResponse());
      }),
    );
    render(<App />);
    await user.click(screen.getByRole("radio", { name: /^Teacher/ }));
    await user.click(screen.getByRole("radio", { name: /^Ghana/ }));
    await user.click(screen.getByRole("radio", { name: /^Practice activity/ }));
    await user.click(screen.getByRole("button", { name: "Review my starting point" }));
    await user.click(screen.getByRole("button", { name: /Generate starter activity/ }));
    const traceButton = screen.getAllByRole("button", { name: "Trace curriculum" })[0];
    if (traceButton === undefined) throw new Error("trace button missing");
    await user.click(traceButton);
    expect(await screen.findByText(/Level evidence/)).toBeVisible();
    expect(screen.getByText("Sources: No source file listed")).toBeVisible();
  });

  it("measures the complete anonymous entry funnel without selected values", async () => {
    const user = userEvent.setup();
    const events: AnalyticsEventName[] = [];
    renderReadyApp({
      track: (event) => {
        events.push(event);
      },
    });

    await waitFor(() => {
      expect(events).toEqual(["entry_viewed"]);
    });
    await user.click(screen.getByRole("link", { name: "Countries" }));
    await user.click(screen.getByRole("link", { name: "Why GapSense" }));
    await user.click(screen.getByRole("link", { name: "Start free" }));
    await user.click(screen.getByRole("link", { name: /Plan a free assessment/ }));
    await user.click(screen.getByRole("link", { name: "Explore country coverage" }));
    await user.click(screen.getByRole("radio", { name: /^Teacher/ }));
    await user.click(screen.getByRole("radio", { name: /^Ghana/ }));
    await user.click(screen.getByRole("radio", { name: /^Diagnostic check/ }));
    await user.click(screen.getByRole("button", { name: "Review my starting point" }));
    await user.click(screen.getByRole("button", { name: "Start again" }));

    expect(events).toEqual([
      "entry_viewed",
      "navigation_countries_selected",
      "navigation_principles_selected",
      "navigation_planner_selected",
      "navigation_planner_selected",
      "navigation_countries_selected",
      "planner_role_selected",
      "planner_country_selected",
      "planner_goal_selected",
      "planner_reviewed",
      "planner_reset",
    ]);
    expect(JSON.stringify(events)).not.toMatch(/Ghana|teacher|diagnostic/i);
  });

  it("does not call an incomplete planner state reviewed", async () => {
    const events: AnalyticsEventName[] = [];
    const { container } = renderReadyApp({
      track: (event) => {
        events.push(event);
      },
    });
    await waitFor(() => {
      expect(events).toEqual(["entry_viewed"]);
    });
    const form = container.querySelector("form");
    if (form === null) {
      throw new Error("assessment planner form was not rendered");
    }

    fireEvent.submit(form);

    expect(events).toEqual(["entry_viewed"]);
    expect(screen.queryByText(/starting point is ready/)).not.toBeInTheDocument();
  });

  it("records one entry view through the development StrictMode check", async () => {
    const events: AnalyticsEventName[] = [];
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockRejectedValue(new TypeError("offline")));

    render(
      <StrictMode>
        <App
          analytics={{
            track: (event) => {
              events.push(event);
            },
          }}
        />
      </StrictMode>,
    );

    await waitFor(() => {
      expect(events).toEqual(["entry_viewed"]);
    });
  });

  it("has no automatically detectable document-level accessibility violations", async () => {
    const { container } = renderReadyApp();
    await screen.findByText("Curriculum evidence connected");

    const results = await axe.run(container, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"] },
    });

    expect(results.violations).toEqual([]);
  });
});
