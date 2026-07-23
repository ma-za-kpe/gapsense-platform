export type AnalyticsEventName =
  | "entry_viewed"
  | "navigation_countries_selected"
  | "navigation_principles_selected"
  | "navigation_planner_selected"
  | "planner_role_selected"
  | "planner_country_selected"
  | "planner_goal_selected"
  | "planner_reviewed"
  | "planner_reset"
  | "readiness_retry_selected"
  | "coverage_retry_selected";

export type Analytics = {
  readonly track: (event: AnalyticsEventName) => void;
};

export type AnalyticsMode = "disabled" | "local_aggregate";

export type PrivacySignalSource = {
  readonly connection?: {
    readonly saveData?: boolean;
  };
  readonly doNotTrack?: string | null;
  readonly globalPrivacyControl?: boolean;
};

type BrowserPrivacySignals = {
  readonly doNotTrack?: string | null;
  readonly globalPrivacyControl?: boolean;
  readonly saveData?: boolean;
};

type BrowserAnalyticsOptions = {
  readonly fetcher: typeof fetch;
  readonly mode: AnalyticsMode;
  readonly signals: BrowserPrivacySignals;
};

const analyticsEndpoint = "/api/v1/analytics/events";
const disabledAnalytics: Analytics = {
  track: () => undefined,
};

export function analyticsModeFromEnvironment(value: string | undefined): AnalyticsMode {
  return value === "local_aggregate" ? "local_aggregate" : "disabled";
}

export function readBrowserPrivacySignals(source: PrivacySignalSource): BrowserPrivacySignals {
  return {
    doNotTrack: source.doNotTrack ?? null,
    globalPrivacyControl: source.globalPrivacyControl ?? false,
    saveData: source.connection?.saveData ?? false,
  };
}

function collectionIsAllowed(mode: AnalyticsMode, signals: BrowserPrivacySignals): boolean {
  return (
    mode === "local_aggregate" &&
    signals.globalPrivacyControl !== true &&
    signals.doNotTrack !== "1" &&
    signals.saveData !== true
  );
}

export function createBrowserAnalytics({
  fetcher,
  mode,
  signals,
}: BrowserAnalyticsOptions): Analytics {
  if (!collectionIsAllowed(mode, signals)) {
    return disabledAnalytics;
  }

  return {
    track: (event) => {
      const body = JSON.stringify({
        events: [{ schema_version: "1.0.0", name: event }],
      });
      try {
        void fetcher(analyticsEndpoint, {
          body,
          cache: "no-store",
          credentials: "omit",
          headers: { "Content-Type": "application/json" },
          keepalive: true,
          method: "POST",
          referrerPolicy: "no-referrer",
        }).catch(() => undefined);
      } catch {
        return;
      }
    },
  };
}

export const browserAnalytics = createBrowserAnalytics({
  fetcher: globalThis.fetch.bind(globalThis),
  mode: analyticsModeFromEnvironment(
    (import.meta.env as unknown as { readonly VITE_ANALYTICS_MODE?: string }).VITE_ANALYTICS_MODE,
  ),
  signals: readBrowserPrivacySignals(navigator),
});
