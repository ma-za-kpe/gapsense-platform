const coverageTimeoutMilliseconds = 5_000;

export type RepositoryStatus = "available" | "partial" | "missing" | "invalid";
export type AvailabilityStatus = "present_unverified" | "missing";
export type ReviewStatus = "not_verified" | "human_reviewed";

export type CurriculumLevel = {
  readonly identifier: string;
  readonly name: string;
  readonly official_phase: string;
  readonly scope_note: string;
  readonly review_status: ReviewStatus;
};

export type CurriculumSubject = {
  readonly identifier: string;
  readonly name: string;
  readonly phase: string;
  readonly availability: AvailabilityStatus;
  readonly review_status: ReviewStatus;
};

export type CoverageMatrixEntry = {
  readonly level_identifier: string;
  readonly level_name: string;
  readonly phase: string;
  readonly subject_identifier: string;
  readonly subject_name: string;
  readonly status:
    "missing" | "located" | "extracted" | "structurally_validated" | "human_reviewed";
  readonly evidence_scope: "level";
  readonly source_url: string;
};

export type CountryCoverage = {
  readonly code: "GH" | "UG";
  readonly name: "Ghana" | "Uganda";
  readonly authority: string;
  readonly authority_url: string;
  readonly availability: AvailabilityStatus;
  readonly review_status: ReviewStatus;
  readonly repository_file_count: number;
  readonly levels: readonly CurriculumLevel[];
  readonly subjects: readonly CurriculumSubject[];
  readonly coverage_matrix: readonly CoverageMatrixEntry[];
};

export type CoverageSnapshot = {
  readonly generated_at: string;
  readonly source_version: string | null;
  readonly review_status: ReviewStatus;
};

export type CatalogCoverage = {
  readonly as_of: string;
  readonly scope_status: "official_authority_inventory";
  readonly represented_cells: number;
  readonly total_cells: number;
  readonly evidence_cells: number;
};

export type SourceInventoryRecord = {
  readonly identifier: string;
  readonly country: "GH" | "UG";
  readonly phase: "primary" | "secondary";
  readonly level: string;
  readonly subject: string;
  readonly edition: string;
  readonly source_url: string;
  readonly retrieved_on: string;
  readonly license_status:
    | "all_rights_reserved_permission_required"
    | "official_index_only_document_not_licensed_for_redistribution"
    | "restricted_internal_research_permission_required_for_redistribution";
  readonly artifact_available: boolean;
  readonly artifact_pages: number | null;
  readonly extraction_status:
    "index_only" | "not_extracted" | "normalized_projection_unverified" | "text_present_unverified";
  readonly review_status:
    | "legacy_artifact_byte_verified_provenance_reacquisition_pending"
    | "official_artifact_byte_verified"
    | "official_artifact_byte_verified_document_phase_review_pending"
    | "official_document_identity_pending_binary_comparison"
    | "official_index_and_framework_verified"
    | "official_index_verified";
  readonly known_gap: string;
};

export type SourceInventoryCoverage = {
  readonly as_of: string;
  readonly total_records: number;
  readonly acquired_artifacts: number;
  readonly records: readonly SourceInventoryRecord[];
};

export type CurriculumCoverageReport = {
  readonly repository_status: RepositoryStatus;
  readonly complete: false;
  readonly countries: readonly CountryCoverage[];
  readonly warnings: readonly string[];
  readonly snapshot: CoverageSnapshot;
  readonly catalog: CatalogCoverage | null;
  readonly source_inventory: SourceInventoryCoverage | null;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const isReviewStatus = (value: unknown): value is ReviewStatus =>
  value === "not_verified" || value === "human_reviewed";

const isLevel = (value: unknown): value is CurriculumLevel =>
  isRecord(value) &&
  typeof value.identifier === "string" &&
  typeof value.name === "string" &&
  typeof value.official_phase === "string" &&
  typeof value.scope_note === "string" &&
  value.scope_note.trim() !== "" &&
  isReviewStatus(value.review_status);

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
  isReviewStatus(value.review_status);

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
  value.evidence_scope === "level" &&
  typeof value.source_url === "string";

const isCoverageMatrix = (value: unknown): value is readonly CoverageMatrixEntry[] =>
  Array.isArray(value) &&
  value.every(isCoverageMatrixEntry) &&
  new Set(
    value.map((entry) => `${entry.phase}:${entry.level_identifier}:${entry.subject_identifier}`),
  ).size === value.length;

const utcTimestamp = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;

const isCoverageSnapshot = (value: unknown): value is CoverageSnapshot =>
  isRecord(value) &&
  typeof value.generated_at === "string" &&
  utcTimestamp.test(value.generated_at) &&
  (value.source_version === null ||
    (typeof value.source_version === "string" && value.source_version.length > 0)) &&
  isReviewStatus(value.review_status);

const isCountry = (value: unknown): value is CountryCoverage => {
  if (
    !isRecord(value) ||
    !hasExpectedCountryIdentity(value) ||
    typeof value.authority !== "string" ||
    typeof value.authority_url !== "string" ||
    (value.availability !== "present_unverified" && value.availability !== "missing") ||
    !isReviewStatus(value.review_status) ||
    !Number.isSafeInteger(value.repository_file_count) ||
    Number(value.repository_file_count) < 0 ||
    !isLevelCatalog(value.levels) ||
    !isSubjectCatalog(value.subjects) ||
    !isCoverageMatrix(value.coverage_matrix)
  ) {
    return false;
  }

  const levels = new Map(value.levels.map((level) => [level.identifier, level]));
  const subjects = new Map(
    value.subjects.map((subject) => [`${subject.phase}:${subject.identifier}`, subject]),
  );
  for (const entry of value.coverage_matrix) {
    const level = levels.get(entry.level_identifier);
    const subject = subjects.get(`${entry.phase}:${entry.subject_identifier}`);
    const officialSourcePrefix =
      value.code === "GH" ? "https://nacca.gov.gh/" : "https://ncdc.go.ug/";
    if (
      level?.name !== entry.level_name ||
      subject?.name !== entry.subject_name ||
      !entry.source_url.startsWith(officialSourcePrefix)
    ) {
      return false;
    }
  }

  for (const subject of value.subjects) {
    const records = value.coverage_matrix.filter(
      (entry) => entry.phase === subject.phase && entry.subject_identifier === subject.identifier,
    );
    const expectedAvailability = records.some((entry) => entry.status !== "missing")
      ? "present_unverified"
      : "missing";
    if (records.length === 0 || subject.availability !== expectedAvailability) {
      return false;
    }
  }

  const expectedCountryAvailability = value.coverage_matrix.some(
    (entry) => entry.status !== "missing",
  )
    ? "present_unverified"
    : "missing";
  return value.availability === expectedCountryAvailability;
};

const isoDate = /^\d{4}-\d{2}-\d{2}$/;

const isCatalogCoverage = (value: unknown): value is CatalogCoverage =>
  isRecord(value) &&
  typeof value.as_of === "string" &&
  isoDate.test(value.as_of) &&
  value.scope_status === "official_authority_inventory" &&
  Number.isSafeInteger(value.represented_cells) &&
  Number(value.represented_cells) > 0 &&
  Number.isSafeInteger(value.total_cells) &&
  value.total_cells === value.represented_cells &&
  Number.isSafeInteger(value.evidence_cells) &&
  Number(value.evidence_cells) >= 0 &&
  Number(value.evidence_cells) <= Number(value.total_cells);

const isSourceInventoryRecord = (value: unknown): value is SourceInventoryRecord => {
  if (
    !isRecord(value) ||
    (value.country !== "GH" && value.country !== "UG") ||
    (value.phase !== "primary" && value.phase !== "secondary") ||
    typeof value.identifier !== "string" ||
    typeof value.level !== "string" ||
    typeof value.subject !== "string" ||
    typeof value.edition !== "string" ||
    typeof value.source_url !== "string" ||
    typeof value.retrieved_on !== "string" ||
    !isoDate.test(value.retrieved_on) ||
    !(
      [
        "all_rights_reserved_permission_required",
        "official_index_only_document_not_licensed_for_redistribution",
        "restricted_internal_research_permission_required_for_redistribution",
      ] as const
    ).includes(value.license_status as SourceInventoryRecord["license_status"]) ||
    typeof value.artifact_available !== "boolean" ||
    !(
      value.artifact_pages === null ||
      (Number.isSafeInteger(value.artifact_pages) && Number(value.artifact_pages) > 0)
    ) ||
    !(
      [
        "index_only",
        "not_extracted",
        "normalized_projection_unverified",
        "text_present_unverified",
      ] as const
    ).includes(value.extraction_status as SourceInventoryRecord["extraction_status"]) ||
    !(
      [
        "legacy_artifact_byte_verified_provenance_reacquisition_pending",
        "official_artifact_byte_verified",
        "official_artifact_byte_verified_document_phase_review_pending",
        "official_document_identity_pending_binary_comparison",
        "official_index_and_framework_verified",
        "official_index_verified",
      ] as const
    ).includes(value.review_status as SourceInventoryRecord["review_status"]) ||
    typeof value.known_gap !== "string"
  ) {
    return false;
  }
  const sourcePrefix = value.country === "GH" ? "https://nacca.gov.gh/" : "https://ncdc.go.ug/";
  return (
    value.source_url.startsWith(sourcePrefix) &&
    value.artifact_available === (value.artifact_pages !== null)
  );
};

const isSourceInventory = (value: unknown): value is SourceInventoryCoverage =>
  isRecord(value) &&
  typeof value.as_of === "string" &&
  isoDate.test(value.as_of) &&
  Number.isSafeInteger(value.total_records) &&
  Number(value.total_records) > 0 &&
  Number.isSafeInteger(value.acquired_artifacts) &&
  Number(value.acquired_artifacts) >= 0 &&
  Array.isArray(value.records) &&
  value.records.length === value.total_records &&
  value.records.every(isSourceInventoryRecord) &&
  value.records.every((record) => record.retrieved_on <= (value.as_of as string)) &&
  new Set(value.records.map((record) => record.identifier)).size === value.records.length &&
  value.records.filter((record) => record.artifact_available).length === value.acquired_artifacts;

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
  const hasRelease =
    value.repository_status === "available" || value.repository_status === "partial";
  if (
    (hasRelease &&
      (!isCatalogCoverage(value.catalog) || !isSourceInventory(value.source_inventory))) ||
    (!hasRelease && (value.catalog !== null || value.source_inventory !== null))
  ) {
    return false;
  }
  if (
    !Array.isArray(value.warnings) ||
    !value.warnings.every((warning) => typeof warning === "string") ||
    !isCoverageSnapshot(value.snapshot)
  ) {
    return false;
  }
  if (
    (hasRelease && value.snapshot.source_version === null) ||
    ((value.repository_status === "missing" || value.repository_status === "invalid") &&
      value.snapshot.source_version !== null)
  ) {
    return false;
  }
  if (
    !Array.isArray(value.countries) ||
    value.countries.length !== 2 ||
    !value.countries.every(isCountry)
  ) {
    return false;
  }

  if (new Set(value.countries.map((country) => country.code)).size !== 2) {
    return false;
  }
  if (isCatalogCoverage(value.catalog)) {
    const entries = value.countries.flatMap((country) => country.coverage_matrix);
    return (
      entries.length === value.catalog.total_cells &&
      entries.filter((entry) => entry.status !== "missing").length === value.catalog.evidence_cells
    );
  }
  return value.countries.every(
    (country) => country.subjects.length === 0 && country.coverage_matrix.length === 0,
  );
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
