import axe from "axe-core";
import { StrictMode } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
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

const requestUrl = (input: RequestInfo | URL): string =>
  typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

const renderReadyApp = (analytics?: Analytics) => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockImplementation((input) =>
        Promise.resolve(
          requestUrl(input).includes("/curriculum/coverage") ? coverageResponse() : readyResponse(),
        ),
      ),
  );
  return render(analytics === undefined ? <App /> : <App analytics={analytics} />);
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("GapSense web entry experience", () => {
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
