const coverageTimeoutMilliseconds = 5_000;

export type RepositoryStatus = "available" | "partial" | "missing" | "invalid";
export type AvailabilityStatus = "present_unverified" | "missing";

export type CurriculumLevel = {
  readonly identifier: string;
  readonly name: string;
  readonly official_phase: string;
  readonly review_status: "not_verified";
};

export type CurriculumSubject = {
  readonly identifier: string;
  readonly name: string;
  readonly phase: string;
  readonly availability: AvailabilityStatus;
  readonly review_status: "not_verified";
};

export type CoverageMatrixEntry = {
  readonly level_identifier: string;
  readonly level_name: string;
  readonly phase: string;
  readonly subject_identifier: string;
  readonly subject_name: string;
  readonly status:
    "missing" | "located" | "extracted" | "structurally_validated" | "human_reviewed";
  readonly evidence_scope: "level" | "phase_only";
};

export type CountryCoverage = {
  readonly code: "GH" | "UG";
  readonly name: "Ghana" | "Uganda";
  readonly authority: string;
  readonly authority_url: string;
  readonly availability: AvailabilityStatus;
  readonly review_status: "not_verified";
  readonly repository_file_count: number;
  readonly levels: readonly CurriculumLevel[];
  readonly subjects?: readonly CurriculumSubject[];
  readonly coverage_matrix?: readonly CoverageMatrixEntry[];
};

export type CoverageSnapshot = {
  readonly generated_at: string;
  readonly source_version: string | null;
  readonly review_status: "not_verified";
};

export type CurriculumCoverageReport = {
  readonly repository_status: RepositoryStatus;
  readonly complete: false;
  readonly countries: readonly CountryCoverage[];
  readonly warnings: readonly string[];
  readonly snapshot: CoverageSnapshot;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const isLevel = (value: unknown): value is CurriculumLevel =>
  isRecord(value) &&
  typeof value.identifier === "string" &&
  typeof value.name === "string" &&
  typeof value.official_phase === "string" &&
  value.review_status === "not_verified";

const hasExpectedCountryIdentity = (value: Record<string, unknown>): boolean =>
  (value.code === "GH" && value.name === "Ghana") ||
  (value.code === "UG" && value.name === "Uganda");

const isLevelCatalog = (value: unknown): value is readonly CurriculumLevel[] =>
  Array.isArray(value) &&
  value.length > 0 &&
  value.every(isLevel) &&
  new Set(value.map((level) => level.identifier)).size === value.length;

const isSubject = (value: unknown): value is CurriculumSubject =>
  isRecord(value) &&
  typeof value.identifier === "string" &&
  typeof value.name === "string" &&
  typeof value.phase === "string" &&
  (value.availability === "present_unverified" || value.availability === "missing") &&
  value.review_status === "not_verified";

const isSubjectCatalog = (value: unknown): value is readonly CurriculumSubject[] =>
  Array.isArray(value) &&
  value.every(isSubject) &&
  new Set(value.map((subject) => `${subject.phase}:${subject.identifier}`)).size === value.length;

const isCoverageMatrixEntry = (value: unknown): value is CoverageMatrixEntry =>
  isRecord(value) &&
  typeof value.level_identifier === "string" &&
  typeof value.level_name === "string" &&
  typeof value.phase === "string" &&
  typeof value.subject_identifier === "string" &&
  typeof value.subject_name === "string" &&
  (
    ["missing", "located", "extracted", "structurally_validated", "human_reviewed"] as const
  ).includes(value.status as CoverageMatrixEntry["status"]) &&
  (["level", "phase_only"] as const).includes(
    value.evidence_scope as CoverageMatrixEntry["evidence_scope"],
  );

const isCoverageMatrix = (value: unknown): value is readonly CoverageMatrixEntry[] =>
  Array.isArray(value) && value.every(isCoverageMatrixEntry);

const utcTimestamp = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;

const isCoverageSnapshot = (value: unknown): value is CoverageSnapshot =>
  isRecord(value) &&
  typeof value.generated_at === "string" &&
  utcTimestamp.test(value.generated_at) &&
  (value.source_version === null ||
    (typeof value.source_version === "string" && value.source_version.length > 0)) &&
  value.review_status === "not_verified";

const isCountry = (value: unknown): value is CountryCoverage =>
  isRecord(value) &&
  hasExpectedCountryIdentity(value) &&
  typeof value.authority === "string" &&
  typeof value.authority_url === "string" &&
  (value.availability === "present_unverified" || value.availability === "missing") &&
  value.review_status === "not_verified" &&
  Number.isSafeInteger(value.repository_file_count) &&
  Number(value.repository_file_count) >= 0 &&
  isLevelCatalog(value.levels) &&
  (value.subjects === undefined || isSubjectCatalog(value.subjects)) &&
  (value.coverage_matrix === undefined || isCoverageMatrix(value.coverage_matrix));

const isCoverageReport = (value: unknown): value is CurriculumCoverageReport => {
  if (!isRecord(value) || value.complete !== false) {
    return false;
  }
  if (
    !(["available", "partial", "missing", "invalid"] as const).includes(
      value.repository_status as RepositoryStatus,
    )
  ) {
    return false;
  }
  if (
    !Array.isArray(value.warnings) ||
    !value.warnings.every((warning) => typeof warning === "string")
  ) {
    return false;
  }
  if (!isCoverageSnapshot(value.snapshot)) {
    return false;
  }
  if (
    !Array.isArray(value.countries) ||
    value.countries.length !== 2 ||
    !value.countries.every(isCountry)
  ) {
    return false;
  }

  return new Set(value.countries.map((country) => country.code)).size === 2;
};

export async function getCurriculumCoverage(
  fetcher: typeof fetch = fetch,
): Promise<CurriculumCoverageReport> {
  const response = await fetcher("/api/v1/curriculum/coverage", {
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(coverageTimeoutMilliseconds),
  });

  if (!response.ok) {
    throw new Error(`coverage endpoint returned ${String(response.status)}`);
  }

  const payload: unknown = await response.json();
  if (!isCoverageReport(payload)) {
    throw new Error("coverage endpoint returned an invalid payload");
  }

  return payload;
}
