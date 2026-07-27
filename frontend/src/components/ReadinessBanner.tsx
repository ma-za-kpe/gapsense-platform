import type { ReadinessState } from "../hooks/useReadiness";

type ReadinessBannerProps = {
  readonly status: ReadinessState;
  readonly onRetry: () => void;
};

export function ReadinessBanner({ status, onRetry }: ReadinessBannerProps): React.JSX.Element {
  if (status === "checking") {
    return (
      <aside className="readiness readiness--checking" aria-live="polite">
        <span className="readiness__signal" aria-hidden="true" />
        <div>
          <strong>Checking public evidence</strong>
          <span> The activity sample remains available while this check runs.</span>
        </div>
      </aside>
    );
  }

  if (status === "ready") {
    return (
      <aside className="readiness readiness--ready" aria-live="polite">
        <span className="readiness__signal" aria-hidden="true" />
        <div>
          <strong>Public evidence catalogue connected</strong>
          <span> The read-only public snapshot is available.</span>
        </div>
      </aside>
    );
  }

  return (
    <aside className="readiness readiness--offline" aria-live="polite">
      <span className="readiness__signal" aria-hidden="true" />
      <div>
        <strong>Sample activity still works on this device</strong>
        <span> Public evidence is temporarily unavailable.</span>
      </div>
      <button className="text-button" type="button" onClick={onRetry}>
        Check connection again
      </button>
    </aside>
  );
}
