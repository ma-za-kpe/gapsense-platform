import { useEffect, useState } from "react";

import type { CoverageState } from "../hooks/useCoverage";
import {
  getCurriculumDetail,
  type CurriculumDetail,
  type CurriculumNode,
} from "../services/details";

type CurriculumExplorerProps = {
  readonly state: CoverageState;
  readonly onRetry: () => void;
};

const phaseFor = (level: string): string =>
  level.includes("high") || level.includes("secondary") ? "secondary" : "primary";

const nodeBelongsToStrand = (node: CurriculumNode, strandIdentifier: string): boolean => {
  const normalized = strandIdentifier.toLowerCase();
  const code = node.code.toLowerCase();
  return code.includes(normalized) || node.title.toLowerCase().includes(normalized);
};

export function CurriculumExplorer({ state, onRetry }: CurriculumExplorerProps): React.JSX.Element {
  const countries = state.status === "loaded" ? state.report.countries : [];
  const [countryCode, setCountryCode] = useState<"GH" | "UG">("GH");
  const availableCountries = countries.filter((item) =>
    item.levels.some((level) =>
      item.subjects?.some((subject) => subject.phase === phaseFor(level.identifier)),
    ),
  );
  const country =
    availableCountries.find((item) => item.code === countryCode) ?? availableCountries[0];
  const levels =
    country?.levels.filter((item) =>
      country.subjects?.some((subject) => subject.phase === phaseFor(item.identifier)),
    ) ?? [];
  const [level, setLevel] = useState("");
  const [subject, setSubject] = useState("");
  const firstLevel = levels.at(0);
  const firstLevelIdentifier = firstLevel === undefined ? "" : firstLevel.identifier;
  const selectedLevel = level === "" ? firstLevelIdentifier : level;
  const subjects =
    country?.subjects?.filter((item) => item.phase === phaseFor(selectedLevel)) ?? [];
  const firstSubject = subjects.at(0);
  const firstSubjectIdentifier = firstSubject === undefined ? "" : firstSubject.identifier;
  const selectedSubject = subject === "" ? firstSubjectIdentifier : subject;
  const [detail, setDetail] = useState<CurriculumDetail | null>(null);
  const [detailState, setDetailState] = useState<"idle" | "loading" | "loaded" | "unavailable">(
    "idle",
  );

  useEffect(() => {
    if (country === undefined || selectedLevel === "" || selectedSubject === "") return;
    void Promise.resolve().then(() => setDetailState("loading"));
    const countryName = countryCode === "GH" ? "ghana" : "uganda";
    void getCurriculumDetail(
      `/api/v1/curriculum/${countryName}/${phaseFor(selectedLevel)}/${selectedLevel}/${selectedSubject}`,
    )
      .then((value) => {
        setDetail(value);
        setDetailState("loaded");
      })
      .catch(() => {
        setDetail(null);
        setDetailState("unavailable");
      });
  }, [country, countryCode, selectedLevel, selectedSubject]);

  if (state.status !== "loaded") {
    return (
      <div className="curriculum-explorer__state">
        <strong>Curriculum evidence is loading.</strong>
        <button className="text-button" type="button" onClick={onRetry}>
          Retry coverage details
        </button>
      </div>
    );
  }

  if (country === undefined) {
    return (
      <section className="curriculum-empty" aria-labelledby="curriculum-empty-title">
        <span className="eyebrow">Public evidence boundary</span>
        <h2 id="curriculum-empty-title">No public subject evidence is available yet</h2>
        <p>
          Country-level presence records are available, but no subject record has passed the
          publication boundary for this public catalogue. Empty controls would imply a choice that
          does not exist.
        </p>
        <a className="quiet-link" href="/about#evidence">
          Read how evidence is published
        </a>
      </section>
    );
  }

  return (
    <div className="curriculum-explorer">
      <div className="curriculum-explorer__intro">
        <p>
          Choose a country, level, and subject to inspect the evidence tree from authority source to
          question-ready standard.
        </p>
        <p className="supporting-copy">
          Only extracted or located evidence is shown. Unsupported combinations stay visibly
          unavailable.
        </p>
      </div>
      <fieldset className="curriculum-explorer__controls">
        <legend className="visually-hidden">Curriculum filters</legend>
        <label>
          Country
          <select
            value={country.code}
            onChange={(event) => {
              setCountryCode(event.target.value as "GH" | "UG");
              setLevel("");
              setSubject("");
            }}
          >
            {availableCountries.map((item) => (
              <option value={item.code} key={item.code}>
                {item.name} - {item.code === "GH" ? "NaCCA" : "NCDC"}
              </option>
            ))}
          </select>
        </label>
        <label>
          Level
          <select
            value={selectedLevel}
            onChange={(event) => {
              setLevel(event.target.value);
              setSubject("");
            }}
          >
            {levels.map((item) => (
              <option value={item.identifier} key={item.identifier}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Subject
          <select value={selectedSubject} onChange={(event) => setSubject(event.target.value)}>
            {subjects.map((item) => (
              <option value={item.identifier} key={item.identifier}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </fieldset>
      <div className="curriculum-explorer__status" aria-live="polite">
        {detailState === "idle" ? "Select a curriculum combination." : null}
        {detailState === "loading" ? "Loading the selected curriculum tree..." : null}
        {detailState === "unavailable"
          ? "This combination has no safe extracted detail yet."
          : null}
        {detailState === "loaded" && detail !== null
          ? `${detail.evidence_scope === "level" ? "Level" : "Phase-level"} evidence - ${detail.extraction_status} - ${String(detail.nodes.length)} standards`
          : null}
      </div>
      {detailState === "loaded" && detail !== null ? (
        <div className="curriculum-tree">
          {detail.strands.map((strand) => {
            const strandNodes = detail.nodes.filter((node) =>
              nodeBelongsToStrand(node, strand.identifier),
            );
            return (
              <details className="curriculum-tree__strand" key={strand.identifier} open>
                <summary>
                  <strong>
                    {strand.identifier} - {strand.name}
                  </strong>
                  <span>
                    {String(strand.sub_strands.length)} sub-strands, {String(strandNodes.length)}{" "}
                    standards
                  </span>
                </summary>
                <div className="curriculum-tree__sub-strands">
                  {strand.sub_strands.map((subStrand) => (
                    <span key={subStrand}>{subStrand}</span>
                  ))}
                </div>
                <div className="curriculum-tree__nodes">
                  {strandNodes.map((node) => (
                    <details key={node.code}>
                      <summary>
                        <strong>{node.code}</strong> {node.title}
                      </summary>
                      <div>
                        <span>Content standard: {node.content_standard || "Not recorded"}</span>
                        <span>
                          Prerequisites: {node.prerequisites.join(", ") || "None recorded"}
                        </span>
                        <span>
                          Indicators:{" "}
                          {node.indicators.map((indicator) => indicator.code).join(", ") ||
                            "None recorded"}
                        </span>
                      </div>
                    </details>
                  ))}
                </div>
              </details>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
