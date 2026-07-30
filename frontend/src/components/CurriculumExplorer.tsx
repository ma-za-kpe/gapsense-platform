import { useEffect, useState } from "react";

import type { CoverageState } from "../hooks/useCoverage";
import {
  getCurriculumDetail,
  type CurriculumDetail,
  type CurriculumNode,
  type CurriculumSection,
} from "../services/details";
import type {
  CountryCoverage,
  CoverageMatrixEntry,
  CurriculumCoverageReport,
  SourceInventoryRecord,
} from "../services/coverage";

type CurriculumExplorerProps = {
  readonly state: CoverageState;
  readonly onRetry: () => void;
};

type CurriculumNodeListProps = {
  readonly nodes: readonly CurriculumNode[];
};

const detailStatuses = new Set<CoverageMatrixEntry["status"]>([
  "located",
  "extracted",
  "structurally_validated",
  "human_reviewed",
]);

const statusLabels: Readonly<Record<CoverageMatrixEntry["status"], string>> = {
  missing: "Missing data",
  located: "Official source located",
  extracted: "Extracted, not verified",
  structurally_validated: "Structurally validated",
  human_reviewed: "Human reviewed",
};

function CurriculumCountryCatalogue({
  country,
}: {
  readonly country: CountryCoverage;
}): React.JSX.Element {
  return (
    <article className="curriculum-catalogue__country">
      <h3>
        {country.name} <span>{country.authority}</span>
      </h3>
      <div className="curriculum-catalogue__levels">
        {country.levels.map((level) => {
          const entries = country.coverage_matrix.filter(
            (entry) => entry.level_identifier === level.identifier,
          );
          const sourceUrls = [...new Set(entries.map((entry) => entry.source_url))];
          const evidenceCount = entries.filter((entry) => entry.status !== "missing").length;
          return (
            <details key={level.identifier}>
              <summary>
                <strong>{level.name}</strong>
                <span>
                  {String(evidenceCount)} of {String(entries.length)} with evidence
                </span>
              </summary>
              {sourceUrls.map((sourceUrl) => (
                <a href={sourceUrl} key={sourceUrl} rel="noreferrer" target="_blank">
                  Official authority inventory
                </a>
              ))}
              <p className="curriculum-catalogue__scope-note">{level.scope_note}</p>
              <ul>
                {entries.map((entry) => (
                  <li
                    data-curriculum-cell={`${country.code}:${entry.phase}:${entry.level_identifier}:${entry.subject_identifier}`}
                    key={`${entry.phase}:${entry.level_identifier}:${entry.subject_identifier}`}
                  >
                    <span>{entry.subject_name}</span>
                    <strong data-status={entry.status}>{statusLabels[entry.status]}</strong>
                  </li>
                ))}
              </ul>
            </details>
          );
        })}
      </div>
    </article>
  );
}

function CurriculumCatalogue({
  report,
}: {
  readonly report: CurriculumCoverageReport;
}): React.JSX.Element {
  if (report.catalog === null) {
    return (
      <section className="curriculum-catalogue" aria-labelledby="curriculum-catalogue-title">
        <h2 id="curriculum-catalogue-title">Whole curriculum catalogue unavailable</h2>
        <p>The pinned official-authority inventory did not pass the release boundary.</p>
      </section>
    );
  }
  const explicitGaps = report.catalog.total_cells - report.catalog.evidence_cells;
  return (
    <section className="curriculum-catalogue" aria-labelledby="curriculum-catalogue-title">
      <div className="curriculum-catalogue__header">
        <div>
          <span className="eyebrow">Whole curriculum catalogue</span>
          <h2 id="curriculum-catalogue-title">Every declared Ghana and Uganda curriculum area</h2>
        </div>
        <p>
          <strong>
            {String(report.catalog.represented_cells)} of {String(report.catalog.total_cells)}
          </strong>{" "}
          official-authority cells represented. {String(report.catalog.evidence_cells)} have
          evidence records; {String(explicitGaps)} remain explicit data gaps.
        </p>
      </div>
      <p className="supporting-copy">
        Catalogue representation is not a claim that the underlying curriculum data is complete.
        Each missing area stays visible until evidence passes the release policy. Inventory dated{" "}
        {report.catalog.as_of}.
      </p>
      <div className="curriculum-catalogue__countries">
        {report.countries.map((country) => (
          <CurriculumCountryCatalogue country={country} key={country.code} />
        ))}
      </div>
    </section>
  );
}

const sourceStatusLabels: Readonly<Record<SourceInventoryRecord["extraction_status"], string>> = {
  index_only: "Official index only",
  not_extracted: "Acquired, not extracted",
  normalized_projection_unverified: "Normalized projection, unverified",
  text_present_unverified: "Text present, unverified",
};

const readableIdentifier = (value: string): string =>
  value
    .split(/[-_]/)
    .map((part) => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`)
    .join(" ");

function SourceInventoryCatalogue({
  report,
}: {
  readonly report: CurriculumCoverageReport;
}): React.JSX.Element {
  const inventory = report.source_inventory;
  if (inventory === null) {
    return (
      <section className="source-inventory" aria-labelledby="source-inventory-title">
        <h2 id="source-inventory-title">Data project source inventory unavailable</h2>
        <p>The pinned source catalogue did not pass the release boundary.</p>
      </section>
    );
  }
  return (
    <section className="source-inventory" aria-labelledby="source-inventory-title">
      <div className="source-inventory__header">
        <div>
          <span className="eyebrow">Data project source inventory</span>
          <h2 id="source-inventory-title">Every release-qualified official source record</h2>
        </div>
        <p>
          <strong>{String(inventory.total_records)}</strong> source records are accounted for;{" "}
          <strong>{String(inventory.acquired_artifacts)}</strong> have byte-verified artifacts in
          the data repository.
        </p>
      </div>
      <p className="supporting-copy">
        Artifact presence does not grant redistribution rights or imply extraction, structural
        validation, or educator review. Inventory dated {inventory.as_of}.
      </p>
      <div className="source-inventory__countries">
        {report.countries.map((country) => {
          const records = inventory.records.filter((record) => record.country === country.code);
          const levels = [...new Set(records.map((record) => record.level))];
          return (
            <article key={country.code}>
              <h3>{country.name}</h3>
              {levels.map((level) => {
                const levelRecords = records.filter((record) => record.level === level);
                return (
                  <details key={level}>
                    <summary>
                      <strong>{level}</strong>
                      <span>{String(levelRecords.length)} records</span>
                    </summary>
                    <ul>
                      {levelRecords.map((record) => (
                        <li data-source-record={record.identifier} key={record.identifier}>
                          <div>
                            <strong>{readableIdentifier(record.subject)}</strong>
                            <span>
                              {readableIdentifier(record.phase)} · {record.edition}
                            </span>
                          </div>
                          <span>{sourceStatusLabels[record.extraction_status]}</span>
                          <span>
                            {record.artifact_available ? "Artifact acquired" : "No local artifact"}
                          </span>
                          <span>
                            {record.artifact_pages === null
                              ? "Page count unavailable"
                              : `${String(record.artifact_pages)} official pages`}
                          </span>
                          <a href={record.source_url} rel="noreferrer" target="_blank">
                            Official source
                          </a>
                          <p className="source-inventory__provenance">
                            <code>{record.identifier}</code>
                            <span>Retrieved {record.retrieved_on}</span>
                            <span>Review: {readableIdentifier(record.review_status)}</span>
                            <span>Rights: {readableIdentifier(record.license_status)}</span>
                          </p>
                          <p>{record.known_gap}</p>
                        </li>
                      ))}
                    </ul>
                  </details>
                );
              })}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function CurriculumNodeList({ nodes }: CurriculumNodeListProps): React.JSX.Element {
  const prerequisiteCopy = (node: CurriculumNode): string => {
    if (node.prerequisite_status === "not_stated_by_authority") {
      return "The official source does not state prerequisite relationships for this page.";
    }
    if (node.prerequisite_status === "not_extracted") {
      return "Prerequisite relationships have not been extracted from this record.";
    }
    return node.prerequisites.length > 0
      ? node.prerequisites.join(", ")
      : "The projected relationship set is explicitly empty.";
  };
  return (
    <div className="curriculum-tree__nodes">
      {nodes.map((node) => (
        <details key={node.code}>
          <summary>
            <strong>
              {node.source_page === null
                ? node.code
                : `Official source page ${String(node.source_page)}`}
            </strong>{" "}
            {node.title}
          </summary>
          <div>
            <span>
              Source:{" "}
              {node.source_id === null || node.source_page === null
                ? "Page locator not recorded"
                : `${node.source_id} · page ${String(node.source_page)}`}
            </span>
            <span>Record type: {readableIdentifier(node.record_kind)}</span>
            <span>Prerequisite relationships: {prerequisiteCopy(node)}</span>
            {node.evidence_items.length > 0 ? (
              <div className="curriculum-tree__markers">
                <strong>Native curriculum markers on this page</strong>
                <ul>
                  {node.evidence_items.map((item, index) => (
                    <li key={`${item.kind}:${item.code ?? ""}:${String(index)}`}>
                      <span>{readableIdentifier(item.kind)}</span>
                      {item.code === null ? null : <code>{item.code}</code>}
                      <p>{item.text}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <span>
                No separate native marker was parsed on this page; its complete official text is
                preserved below.
              </span>
            )}
            {node.indicators.length > 0 ? (
              <div className="curriculum-tree__markers">
                <strong>Curated indicators</strong>
                <ul>
                  {node.indicators.map((indicator) => (
                    <li key={indicator.code}>
                      <code>{indicator.code}</code>
                      <p>{indicator.title}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <details className="curriculum-tree__source-text">
              <summary>Read complete official page text</summary>
              <pre>{node.content_standard}</pre>
            </details>
          </div>
        </details>
      ))}
    </div>
  );
}

type CurriculumSectionBranchProps = {
  readonly section: CurriculumSection;
  readonly sectionsByParent: ReadonlyMap<string, readonly CurriculumSection[]>;
  readonly nodesBySection: ReadonlyMap<string, readonly CurriculumNode[]>;
  readonly depth: number;
};

function CurriculumSectionBranch({
  section,
  sectionsByParent,
  nodesBySection,
  depth,
}: CurriculumSectionBranchProps): React.JSX.Element {
  const children = sectionsByParent.get(section.identifier) ?? [];
  const nodes = nodesBySection.get(section.identifier) ?? [];
  return (
    <details className="curriculum-tree__section" data-section-kind={section.kind} open={depth < 2}>
      <summary>
        <strong>{section.title}</strong>
        <span>
          {readableIdentifier(section.kind)} · {String(children.length)} branches ·{" "}
          {String(nodes.length)} direct pages
        </span>
      </summary>
      <p className="curriculum-tree__section-source">
        First evidenced at {section.source_id} · page {String(section.source_page)}
      </p>
      {children.map((child) => (
        <CurriculumSectionBranch
          depth={depth + 1}
          key={child.identifier}
          nodesBySection={nodesBySection}
          section={child}
          sectionsByParent={sectionsByParent}
        />
      ))}
      {nodes.length > 0 ? <CurriculumNodeList nodes={nodes} /> : null}
    </details>
  );
}

function CountryNativeCurriculumTree({
  detail,
}: {
  readonly detail: CurriculumDetail;
}): React.JSX.Element {
  const sectionsByParent = new Map<string, CurriculumSection[]>();
  for (const section of detail.sections) {
    if (section.parent_identifier === null) continue;
    const children = sectionsByParent.get(section.parent_identifier) ?? [];
    children.push(section);
    sectionsByParent.set(section.parent_identifier, children);
  }
  const nodesBySection = new Map<string, CurriculumNode[]>();
  for (const node of detail.nodes) {
    if (node.section_identifier === null) continue;
    const nodes = nodesBySection.get(node.section_identifier) ?? [];
    nodes.push(node);
    nodesBySection.set(node.section_identifier, nodes);
  }
  const roots = detail.sections.filter((section) => section.parent_identifier === null);
  const unassignedNodes = detail.nodes.filter((node) => node.section_identifier === null);

  return (
    <>
      <header className="curriculum-tree__model">
        <span className="eyebrow">Country-native curriculum model</span>
        <h2>{readableIdentifier(detail.curriculum_model)}</h2>
        <p>
          {String(detail.sections.length)} traced structural sections index{" "}
          {String(detail.nodes.length)} complete source pages. Structure status:{" "}
          {readableIdentifier(detail.structure_status)}.
        </p>
        <p>Text extraction: {readableIdentifier(detail.extraction_method)}.</p>
      </header>
      {roots.map((root) => (
        <CurriculumSectionBranch
          depth={0}
          key={root.identifier}
          nodesBySection={nodesBySection}
          section={root}
          sectionsByParent={sectionsByParent}
        />
      ))}
      {unassignedNodes.length > 0 ? (
        <details className="curriculum-tree__section">
          <summary>
            <strong>Unassigned source evidence</strong>
            <span>{String(unassignedNodes.length)} pages</span>
          </summary>
          <CurriculumNodeList nodes={unassignedNodes} />
        </details>
      ) : null}
    </>
  );
}

export function CurriculumExplorer({ state, onRetry }: CurriculumExplorerProps): React.JSX.Element {
  const countries = state.status === "loaded" ? state.report.countries : [];
  const sourceVersion = state.status === "loaded" ? state.report.snapshot.source_version : null;
  const [countryCode, setCountryCode] = useState<"GH" | "UG">("GH");
  const availableCountries =
    state.status === "loaded" && state.report.catalog !== null ? countries : [];
  const country =
    availableCountries.find((item) => item.code === countryCode) ?? availableCountries[0];
  const availableEntries = country?.coverage_matrix ?? [];
  const levels =
    country?.levels.filter((item) =>
      availableEntries.some((entry) => entry.level_identifier === item.identifier),
    ) ?? [];
  const [level, setLevel] = useState("");
  const [subject, setSubject] = useState("");
  const preferredEntry = availableEntries.find((entry) => detailStatuses.has(entry.status));
  const firstLevel =
    levels.find((item) => item.identifier === preferredEntry?.level_identifier) ?? levels.at(0);
  const firstLevelIdentifier = firstLevel === undefined ? "" : firstLevel.identifier;
  const selectedLevel = levels.some((item) => item.identifier === level)
    ? level
    : firstLevelIdentifier;
  const subjects =
    country?.subjects.filter((item) =>
      availableEntries.some(
        (entry) =>
          entry.level_identifier === selectedLevel &&
          entry.subject_identifier === item.identifier &&
          entry.phase === item.phase,
      ),
    ) ?? [];
  const firstSubject =
    subjects.find((item) => item.identifier === preferredEntry?.subject_identifier) ??
    subjects.at(0);
  const firstSubjectIdentifier = firstSubject === undefined ? "" : firstSubject.identifier;
  const selectedSubject = subjects.some((item) => item.identifier === subject)
    ? subject
    : firstSubjectIdentifier;
  const selectedEntry = availableEntries.find(
    (entry) =>
      entry.level_identifier === selectedLevel && entry.subject_identifier === selectedSubject,
  );
  const [detail, setDetail] = useState<CurriculumDetail | null>(null);
  const [detailState, setDetailState] = useState<"idle" | "loading" | "loaded" | "unavailable">(
    "idle",
  );

  useEffect(() => {
    if (country === undefined || selectedEntry === undefined) return;
    if (!detailStatuses.has(selectedEntry.status)) {
      void Promise.resolve().then(() => {
        setDetail(null);
        setDetailState("unavailable");
      });
      return;
    }
    const controller = new AbortController();
    void Promise.resolve().then(() => {
      if (!controller.signal.aborted) {
        setDetail(null);
        setDetailState("loading");
      }
    });
    const countryName = country.code === "GH" ? "ghana" : "uganda";
    void getCurriculumDetail(
      `/api/v1/curriculum/${countryName}/${selectedEntry.phase}/${selectedEntry.level_identifier}/${selectedEntry.subject_identifier}`,
      controller.signal,
    )
      .then((value) => {
        if (
          value.release_id !== sourceVersion ||
          value.country !== countryName ||
          value.phase !== selectedEntry.phase ||
          value.level !== selectedEntry.level_identifier ||
          value.subject !== selectedEntry.subject_identifier
        ) {
          throw new Error("Curriculum detail identity does not match the active selection");
        }
        if (!controller.signal.aborted) {
          setDetail(value);
          setDetailState("loaded");
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setDetail(null);
          setDetailState("unavailable");
        }
      });
    return () => controller.abort();
  }, [country, selectedEntry, sourceVersion]);

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
      <div className="curriculum-explorer">
        <section className="curriculum-empty" aria-labelledby="curriculum-empty-title">
          <span className="eyebrow">Detail evidence boundary</span>
          <h2 id="curriculum-empty-title">No safely projected subject detail is available yet</h2>
          <p>
            The whole official-authority catalogue remains visible below. Detail controls appear for
            every declared combination when the release catalogue is available; missing records
            remain explicit and cannot open an invented tree.
          </p>
          <a className="quiet-link" href="/about#evidence">
            Read how evidence is published
          </a>
        </section>
        <CurriculumCatalogue report={state.report} />
        <SourceInventoryCatalogue report={state.report} />
      </div>
    );
  }

  return (
    <div className="curriculum-explorer">
      <div className="curriculum-explorer__intro">
        <p>
          Choose a country, level, and subject to inspect release-qualified curriculum records and
          their authority source pages.
        </p>
        <p className="supporting-copy">
          Every declared combination is selectable. Extracted records open their byte-pinned
          evidence; authority-located records explain the exact publication boundary without
          inventing detail.
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
          ? selectedEntry?.status === "missing"
            ? "This official curriculum area is catalogued, but release-qualified detail is unavailable."
            : "Curriculum detail could not be loaded. Its official catalogue record remains available below."
          : null}
        {detailState === "loaded" && detail !== null
          ? detail.extraction_status === "located"
            ? "Official curriculum area confirmed; the authority does not currently expose a downloadable subject syllabus."
            : `Level evidence - extracted - ${String(detail.nodes.length)} source pages`
          : null}
      </div>
      {detailState === "loaded" && detail !== null ? (
        <div className="curriculum-tree">
          {detail.extraction_status === "located" ? (
            <section className="curriculum-empty" aria-labelledby="located-curriculum-title">
              <span className="eyebrow">Official authority boundary</span>
              <h2 id="located-curriculum-title">
                {readableIdentifier(detail.subject)} is represented
              </h2>
              <p>
                The authority catalogue confirms this curriculum area, but no complete subject
                syllabus artifact is exposed for byte-pinned extraction. No curriculum tree has been
                invented.
              </p>
              <a href={country.authority_url} rel="noreferrer" target="_blank">
                View the official authority inventory
              </a>
            </section>
          ) : null}
          {detail.extraction_status === "extracted" ? (
            <CountryNativeCurriculumTree detail={detail} />
          ) : null}
        </div>
      ) : null}
      <CurriculumCatalogue report={state.report} />
      <SourceInventoryCatalogue report={state.report} />
    </div>
  );
}
