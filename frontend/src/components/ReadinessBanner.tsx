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
          <strong>Checking local curriculum evidence</strong>
          <span> Your planning choices stay on this device.</span>
        </div>
      </aside>
    );
  }

  if (status === "ready") {
    return (
      <aside className="readiness readiness--ready" aria-live="polite">
        <span className="readiness__signal" aria-hidden="true" />
        <div>
          <strong>Curriculum evidence connected</strong>
          <span> The local, read-only evidence repository is available.</span>
        </div>
      </aside>
    );
  }

  return (
    <aside className="readiness readiness--offline" aria-live="polite">
      <span className="readiness__signal" aria-hidden="true" />
      <div>
        <strong>Planning still works locally</strong>
        <span> Curriculum evidence is temporarily unavailable.</span>
      </div>
      <button className="text-button" type="button" onClick={onRetry}>
        Check connection again
      </button>
    </aside>
  );
}
