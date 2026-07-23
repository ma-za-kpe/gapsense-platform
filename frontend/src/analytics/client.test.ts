import { waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  analyticsModeFromEnvironment,
  createBrowserAnalytics,
  readBrowserPrivacySignals,
  type AnalyticsEventName,
} from "./client";

const allEvents: readonly AnalyticsEventName[] = [
  "entry_viewed",
  "navigation_countries_selected",
  "navigation_principles_selected",
  "navigation_planner_selected",
  "planner_role_selected",
  "planner_country_selected",
  "planner_goal_selected",
  "planner_reviewed",
  "planner_reset",
  "readiness_retry_selected",
  "coverage_retry_selected",
];

describe("privacy-safe browser analytics", () => {
  it("keeps collection disabled unless local aggregate mode is exact", () => {
    const fetcher = vi.fn<typeof fetch>();
    expect(analyticsModeFromEnvironment(undefined)).toBe("disabled");
    expect(analyticsModeFromEnvironment("enabled")).toBe("disabled");
    expect(analyticsModeFromEnvironment("local_aggregate")).toBe("local_aggregate");

    createBrowserAnalytics({
      fetcher,
      mode: "disabled",
      signals: {},
    }).track("entry_viewed");

    expect(fetcher).not.toHaveBeenCalled();
  });

  it.each([
    { label: "Global Privacy Control", signals: { globalPrivacyControl: true } },
    { label: "Do Not Track", signals: { doNotTrack: "1" } },
    { label: "reduced-data preference", signals: { saveData: true } },
  ] as const)("sends nothing when $label is active", ({ signals }) => {
    const fetcher = vi.fn<typeof fetch>();
    const analytics = createBrowserAnalytics({
      fetcher,
      mode: "local_aggregate",
      signals,
    });

    analytics.track("entry_viewed");

    expect(fetcher).not.toHaveBeenCalled();
  });

  it("reads only explicit browser privacy signals", () => {
    expect(
      readBrowserPrivacySignals({
        connection: { saveData: true },
        doNotTrack: "1",
        globalPrivacyControl: true,
      }),
    ).toEqual({
      doNotTrack: "1",
      globalPrivacyControl: true,
      saveData: true,
    });
    expect(readBrowserPrivacySignals({})).toEqual({
      doNotTrack: null,
      globalPrivacyControl: false,
      saveData: false,
    });
  });

  it("posts each allowlisted name to the bounded same-origin contract", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 204 }));
    const analytics = createBrowserAnalytics({
      fetcher,
      mode: "local_aggregate",
      signals: {},
    });

    for (const event of allEvents) {
      analytics.track(event);
    }

    await waitFor(() => {
      expect(fetcher).toHaveBeenCalledTimes(allEvents.length);
    });
    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "/api/v1/analytics/events",
      expect.objectContaining({
        body: JSON.stringify({
          events: [{ schema_version: "1.0.0", name: "entry_viewed" }],
        }),
        cache: "no-store",
        credentials: "omit",
        headers: { "Content-Type": "application/json" },
        keepalive: true,
        method: "POST",
        referrerPolicy: "no-referrer",
      }),
    );
  });

  it("never lets rejected or synchronous transport failures break an action", async () => {
    const rejectedFetch = vi.fn<typeof fetch>().mockRejectedValueOnce(new TypeError("offline"));
    const rejectedAnalytics = createBrowserAnalytics({
      fetcher: rejectedFetch,
      mode: "local_aggregate",
      signals: {},
    });
    const throwingFetch = vi.fn<typeof fetch>(() => {
      throw new TypeError("unavailable");
    });
    const throwingAnalytics = createBrowserAnalytics({
      fetcher: throwingFetch,
      mode: "local_aggregate",
      signals: {},
    });

    expect(() => {
      rejectedAnalytics.track("planner_reviewed");
      throwingAnalytics.track("planner_reset");
    }).not.toThrow();
    await waitFor(() => {
      expect(rejectedFetch).toHaveBeenCalledOnce();
    });
    expect(throwingFetch).toHaveBeenCalledOnce();
  });
});
