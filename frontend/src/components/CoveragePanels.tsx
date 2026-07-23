import { countryProfiles } from "../domain/planner";
import type { CoverageState } from "../hooks/useCoverage";
import type { CountryCoverage } from "../services/coverage";

type CoveragePanelsProps = {
  readonly state: CoverageState;
  readonly onRetry: () => void;
};

const fileStatus = (country: CountryCoverage): string => {
  if (country.repository_file_count === 0) {
    return "No canonical repository files located";
  }
  return `${String(country.repository_file_count)} repository ${country.repository_file_count === 1 ? "file" : "files"} located`;
};

function LoadedCountryPanel({ country }: { readonly country: CountryCoverage }): React.JSX.Element {
  const accent = country.code === "GH" ? "gold" : "coral";
  const authorityLabel = country.code === "GH" ? "NaCCA" : "NCDC";

  return (
    <article className={`country-panel country-panel--${accent}`}>
      <div className="country-panel__index" aria-hidden="true">
        {country.code}
      </div>
      <span className="country-panel__authority">{authorityLabel}</span>
      <h3>{country.name}</h3>
      <p>{country.authority}</p>
      <ul aria-label={`${country.name} official level structure`}>
        {country.levels.map((level) => (
          <li key={level.identifier} title={level.official_phase}>
            {level.name}
          </li>
        ))}
      </ul>
      <div className="country-panel__status">
        <span className="country-panel__signal" aria-hidden="true" />
        <div>
          <strong>{fileStatus(country)}</strong>
          <small>Extraction and educator review not verified</small>
        </div>
      </div>
    </article>
  );
}

function PendingCountryPanels({ loading }: { readonly loading: boolean }): React.JSX.Element {
  return (
    <>
      {Object.values(countryProfiles).map((country) => (
        <article className={`country-panel country-panel--${country.accent}`} key={country.name}>
          <div className="country-panel__index" aria-hidden="true">
            {country.name === "Ghana" ? "GH" : "UG"}
          </div>
          <span className="country-panel__authority">{country.authority}</span>
          <h3>{country.name}</h3>
          <p>{country.authorityLongName}</p>
          <ul aria-label={`${country.name} initial level structure`}>
            {country.levels.map((level) => (
              <li key={level}>{level}</li>
            ))}
          </ul>
          <div className="country-panel__status">
            <span className="country-panel__signal" aria-hidden="true" />
            <div>
              <strong>
                {loading ? "Checking local coverage evidence…" : "Coverage details unavailable"}
              </strong>
              <small>Extraction and educator review not verified</small>
            </div>
          </div>
        </article>
      ))}
    </>
  );
}

export function CoveragePanels({ state, onRetry }: CoveragePanelsProps): React.JSX.Element {
  if (state.status === "loaded") {
    return (
      <div className="country-showcase">
        {state.report.countries.map((country) => (
          <LoadedCountryPanel country={country} key={country.code} />
        ))}
      </div>
    );
  }

  return (
    <>
      {state.status === "unavailable" ? (
        <div className="coverage-alert" role="alert">
          <div>
            <strong>Live coverage details are unavailable</strong>
            <span> Country context stays visible, but no repository claim is being made.</span>
          </div>
          <button className="text-button" type="button" onClick={onRetry}>
            Retry coverage details
          </button>
        </div>
      ) : null}
      <div className="country-showcase" aria-busy={state.status === "loading"}>
        <PendingCountryPanels loading={state.status === "loading"} />
      </div>
    </>
  );
}
