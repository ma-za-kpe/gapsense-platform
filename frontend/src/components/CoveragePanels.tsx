import { useState } from "react";

import { countryProfiles } from "../domain/planner";
import type { CoverageState } from "../hooks/useCoverage";
import type { CountryCoverage } from "../services/coverage";

type CoveragePanelsProps = {
  readonly state: CoverageState;
  readonly onRetry: () => void;
};

const publicationStatus = (country: CountryCoverage): string => {
  if (country.availability === "missing") {
    return "No public evidence is available yet";
  }
  const subjectCount = country.subjects.filter(
    (subject) => subject.availability === "present_unverified",
  ).length;
  if (subjectCount === 0) {
    return "No exact subject record is available yet";
  }
  const reviewLabel = country.review_status === "human_reviewed" ? "reviewed" : "unreviewed";
  return `${String(subjectCount)} ${reviewLabel} subject ${subjectCount === 1 ? "record is" : "records are"} visible`;
};

const formatSnapshotDate = (timestamp: string): string =>
  new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(timestamp));

const matrixSummary = (entries: CountryCoverage["coverage_matrix"]): string => {
  const extracted = entries.filter((entry) => entry.status === "extracted").length;
  const located = entries.filter((entry) => entry.status === "located").length;
  const missing = entries.filter((entry) => entry.status === "missing").length;
  return `${String(extracted)} extracted · ${String(located)} located · ${String(missing)} explicitly missing`;
};

const organizationExamples = {
  GH: {
    title: "Planned NaCCA evidence structure",
    steps: [
      "Country and authority",
      "Key phase / Basic level",
      "Subject",
      "Strand and sub-strand",
      "Content standard and indicator",
      "Question, answer key, and review record",
    ],
    note: "This is the intended organization for future reviewed Ghana evidence, not a claim that these layers are publicly available.",
  },
  UG: {
    title: "Planned NCDC evidence structure",
    steps: [
      "Country and authority",
      "Curriculum phase / primary level",
      "Learning area or subject",
      "Theme, topic, or strand",
      "Learning outcome and prerequisite",
      "Question, answer key, and review record",
    ],
    note: "This is the intended organization for future reviewed Uganda evidence, not a claim that these layers are publicly available.",
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
  const evidenceSubjects = country.subjects.filter((subject) => subject.availability !== "missing");

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
        {evidenceSubjects.length ? (
          <details className="country-panel__subject-list">
            <summary>View all {String(evidenceSubjects.length)} evidence subject records</summary>
            <ul aria-label={`${country.name} subjects found in public evidence`}>
              {evidenceSubjects.map((subject) => (
                <li key={`${subject.phase}:${subject.identifier}`}>
                  {subject.name} <small>({subject.phase})</small>
                </li>
              ))}
            </ul>
          </details>
        ) : (
          <p>No subject records are currently visible in the public evidence catalogue.</p>
        )}
        <small>Presence is not the same as extraction or educator review.</small>
      </div>
      {country.coverage_matrix.length ? (
        <details
          className="coverage-matrix"
          open={matrixOpen}
          onToggle={(event) => onMatrixToggle(event.currentTarget.open)}
        >
          <summary>See level and subject evidence matrix</summary>
          <div className="coverage-matrix__body">
            <p>
              Every row is one exact level and subject declaration. “Extracted” means byte-pinned
              normalized curriculum nodes exist; “located” means the official source is known but
              has no projection; “missing” records an explicit data gap. No status implies educator
              review.
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
                      <td>exact level</td>
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
          <strong>{publicationStatus(country)}</strong>
          <small>
            {country.review_status === "human_reviewed"
              ? "Human review has been recorded."
              : "No educator review has been recorded."}
          </small>
        </div>
      </div>
      <details className="curriculum-map">
        <summary>See planned evidence structure</summary>
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
                {loading ? "Checking public coverage evidence…" : "Coverage details unavailable"}
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
      <>
        <aside className="coverage-provenance" role="note" aria-label="Evidence snapshot">
          <strong>Evidence snapshot</strong>
          <span>
            Catalogue checked{" "}
            <time dateTime={state.report.snapshot.generated_at}>
              {formatSnapshotDate(state.report.snapshot.generated_at)}
            </time>
          </span>
          <span>
            {state.report.snapshot.source_version === null
              ? "Data release identity is not available"
              : `Data release: ${state.report.snapshot.source_version}`}
          </span>
          <span>
            {state.report.snapshot.review_status === "human_reviewed"
              ? "Human review is recorded for this snapshot."
              : "No human review is recorded for this snapshot."}
          </span>
        </aside>
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
      </>
    );
  }

  return (
    <>
      {state.status === "unavailable" ? (
        <div className="coverage-alert" role="alert">
          <div>
            <strong>Public coverage details are unavailable</strong>
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
