import { useState } from "react";

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

const matrixSummary = (
  entries: readonly NonNullable<CountryCoverage["coverage_matrix"]>[number][],
): string => {
  const extracted = entries.filter((entry) => entry.status === "extracted").length;
  const located = entries.filter((entry) => entry.status === "located").length;
  const missing = entries.filter((entry) => entry.status === "missing").length;
  return `${String(extracted)} extracted · ${String(located)} located at phase scope · ${String(missing)} missing subject folders`;
};

const organizationExamples = {
  GH: {
    title: "NaCCA standards-based structure",
    steps: [
      "Country and authority",
      "Key phase / Basic level",
      "Subject",
      "Strand and sub-strand",
      "Content standard and indicator",
      "Question, answer key, and review record",
    ],
    note: "Ghana evidence is being catalogued from NaCCA standards and official subject documents.",
  },
  UG: {
    title: "NCDC phase-based structure",
    steps: [
      "Country and authority",
      "Curriculum phase / primary level",
      "Learning area or subject",
      "Theme, topic, or strand",
      "Learning outcome and prerequisite",
      "Question, answer key, and review record",
    ],
    note: "Uganda Primary 1–3 uses thematic learning; later primary and secondary phases use more subject-based structures.",
  },
} as const;

function LoadedCountryPanel({
  country,
  matrixOpen,
  onMatrixToggle,
}: {
  readonly country: CountryCoverage;
  readonly matrixOpen: boolean;
  readonly onMatrixToggle: (open: boolean) => void;
}): React.JSX.Element {
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
      <div className="country-panel__subjects">
        <strong>Evidence subjects found</strong>
        {country.subjects?.length ? (
          <ul aria-label={`${country.name} subjects found in local evidence`}>
            {country.subjects.map((subject) => (
              <li key={`${subject.phase}:${subject.identifier}`}>
                {subject.name} <small>({subject.phase})</small>
              </li>
            ))}
          </ul>
        ) : (
          <p>No subject folders are currently visible in the local evidence mount.</p>
        )}
        <small>Presence is not the same as extraction or educator review.</small>
      </div>
      {country.coverage_matrix?.length ? (
        <details
          className="coverage-matrix"
          open={matrixOpen}
          onToggle={(event) => onMatrixToggle(event.currentTarget.open)}
        >
          <summary>See level and subject evidence matrix</summary>
          <div className="coverage-matrix__body">
            <p>
              Level-specific evidence is shown separately from phase-level folders. “Extracted”
              means normalized curriculum nodes exist; “located” means an official subject folder
              exists only at phase scope; “missing” means no subject folder exists in the local
              evidence repository. No status implies educator review.
            </p>
            <p className="coverage-matrix__summary">{matrixSummary(country.coverage_matrix)}</p>
            <div className="coverage-matrix__table-wrap">
              <table>
                <caption>{country.name} level and subject evidence</caption>
                <thead>
                  <tr>
                    <th scope="col">Level</th>
                    <th scope="col">Subject</th>
                    <th scope="col">Status</th>
                    <th scope="col">Evidence scope</th>
                  </tr>
                </thead>
                <tbody>
                  {country.coverage_matrix.map((entry) => (
                    <tr key={`${entry.level_identifier}:${entry.subject_identifier}`}>
                      <th scope="row">{entry.level_name}</th>
                      <td>{entry.subject_name}</td>
                      <td>{entry.status.replaceAll("_", " ")}</td>
                      <td>
                        {entry.evidence_scope === "phase_only"
                          ? "phase folder only"
                          : "level folder"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="coverage-matrix__next-step">
              The complete acquisition queue is maintained in the data repository and is being
              closed subject by subject; unsupported questions remain disabled.
            </p>
          </div>
        </details>
      ) : null}
      <div className="country-panel__status">
        <span className="country-panel__signal" aria-hidden="true" />
        <div>
          <strong>{fileStatus(country)}</strong>
          <small>Extraction and educator review not verified</small>
        </div>
      </div>
      <details className="curriculum-map">
        <summary>See how questions are organised</summary>
        <div className="curriculum-map__body">
          <strong>{organizationExamples[country.code].title}</strong>
          <ol>
            {organizationExamples[country.code].steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <p>{organizationExamples[country.code].note}</p>
          <a href={country.authority_url} target="_blank" rel="noreferrer">
            Open {country.name} authority source <span aria-hidden="true">↗</span>
          </a>
        </div>
      </details>
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
  const [openCountry, setOpenCountry] = useState<CountryCoverage["code"] | null>(null);
  if (state.status === "loaded") {
    return (
      <div className="country-showcase">
        {state.report.countries.map((country) => (
          <LoadedCountryPanel
            country={country}
            key={country.code}
            matrixOpen={openCountry === country.code}
            onMatrixToggle={(open) => setOpenCountry(open ? country.code : null)}
          />
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
