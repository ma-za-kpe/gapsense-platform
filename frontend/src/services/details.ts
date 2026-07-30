const detailTimeoutMilliseconds = 5_000;

export type CurriculumIndicator = {
  readonly code: string;
  readonly title: string;
  readonly question_type: string | null;
  readonly difficulty: number | null;
  readonly misconception_count: number;
};

export type CurriculumEvidenceItem = {
  readonly kind: string;
  readonly code: string | null;
  readonly text: string;
};

export type CurriculumNode = {
  readonly code: string;
  readonly title: string;
  readonly record_kind: string;
  readonly content_standard: string;
  readonly source_id: string | null;
  readonly source_page: number | null;
  readonly curriculum_path: readonly string[];
  readonly section_identifier: string | null;
  readonly strand_identifier: string | null;
  readonly prerequisite_status:
    "not_stated_by_authority" | "projected_relationships" | "not_extracted";
  readonly prerequisites: readonly string[];
  readonly evidence_items: readonly CurriculumEvidenceItem[];
  readonly indicators: readonly CurriculumIndicator[];
};

export type CurriculumSection = {
  readonly identifier: string;
  readonly parent_identifier: string | null;
  readonly kind: string;
  readonly title: string;
  readonly source_id: string;
  readonly source_page: number;
};

export type CurriculumStrand = {
  readonly identifier: string;
  readonly name: string;
  readonly sub_strands: readonly string[];
};

export type CurriculumDetail = {
  readonly release_id: string;
  readonly country: string;
  readonly phase: string;
  readonly level: string;
  readonly subject: string;
  readonly evidence_scope: "level";
  readonly extraction_status: "located" | "extracted";
  readonly extraction_method: string;
  readonly source_files: readonly string[];
  readonly curriculum_model: string;
  readonly structure_status: string;
  readonly sections: readonly CurriculumSection[];
  readonly strands: readonly CurriculumStrand[];
  readonly nodes: readonly CurriculumNode[];
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const isNullableString = (value: unknown): value is string | null =>
  value === null || typeof value === "string";

const isNullableNumber = (value: unknown): value is number | null =>
  value === null || (typeof value === "number" && Number.isFinite(value));

const isIndicator = (value: unknown): value is CurriculumIndicator =>
  isRecord(value) &&
  typeof value.code === "string" &&
  typeof value.title === "string" &&
  isNullableString(value.question_type) &&
  isNullableNumber(value.difficulty) &&
  Number.isSafeInteger(value.misconception_count) &&
  Number(value.misconception_count) >= 0;

const isEvidenceItem = (value: unknown): value is CurriculumEvidenceItem =>
  isRecord(value) &&
  typeof value.kind === "string" &&
  value.kind.length > 0 &&
  isNullableString(value.code) &&
  typeof value.text === "string" &&
  value.text.length > 0;

const isSection = (value: unknown): value is CurriculumSection =>
  isRecord(value) &&
  typeof value.identifier === "string" &&
  value.identifier.length > 0 &&
  isNullableString(value.parent_identifier) &&
  typeof value.kind === "string" &&
  value.kind.length > 0 &&
  typeof value.title === "string" &&
  value.title.length > 0 &&
  typeof value.source_id === "string" &&
  value.source_id.length > 0 &&
  Number.isSafeInteger(value.source_page) &&
  Number(value.source_page) > 0;

const isStrand = (value: unknown): value is CurriculumStrand =>
  isRecord(value) &&
  typeof value.identifier === "string" &&
  typeof value.name === "string" &&
  Array.isArray(value.sub_strands) &&
  value.sub_strands.every((item) => typeof item === "string");

const isNode = (value: unknown): value is CurriculumNode => {
  if (
    !isRecord(value) ||
    typeof value.code !== "string" ||
    typeof value.title !== "string" ||
    typeof value.record_kind !== "string" ||
    value.record_kind.length === 0 ||
    typeof value.content_standard !== "string" ||
    !isNullableString(value.source_id) ||
    !isNullableNumber(value.source_page) ||
    !Array.isArray(value.curriculum_path) ||
    !value.curriculum_path.every((item) => typeof item === "string") ||
    !isNullableString(value.section_identifier) ||
    !isNullableString(value.strand_identifier) ||
    !["not_stated_by_authority", "projected_relationships", "not_extracted"].includes(
      String(value.prerequisite_status),
    ) ||
    !Array.isArray(value.prerequisites) ||
    !value.prerequisites.every((item) => typeof item === "string") ||
    !Array.isArray(value.evidence_items) ||
    !value.evidence_items.every(isEvidenceItem) ||
    !Array.isArray(value.indicators) ||
    !value.indicators.every(isIndicator)
  ) {
    return false;
  }
  const hasSourceId = value.source_id !== null && value.source_id.length > 0;
  const hasSourcePage =
    value.source_page !== null && Number.isSafeInteger(value.source_page) && value.source_page > 0;
  return (value.source_id === null && value.source_page === null) || (hasSourceId && hasSourcePage);
};

const hasUniqueIdentifiers = (values: readonly { readonly identifier: string }[]): boolean =>
  new Set(values.map((value) => value.identifier)).size === values.length;

const hasUniqueCodes = (values: readonly { readonly code: string }[]): boolean =>
  new Set(values.map((value) => value.code)).size === values.length;

const isDetail = (value: unknown): value is CurriculumDetail => {
  if (!isRecord(value)) return false;
  if (
    typeof value.release_id !== "string" ||
    value.release_id.length === 0 ||
    typeof value.country !== "string" ||
    typeof value.phase !== "string" ||
    typeof value.level !== "string" ||
    typeof value.subject !== "string" ||
    value.evidence_scope !== "level" ||
    (value.extraction_status !== "located" && value.extraction_status !== "extracted") ||
    typeof value.extraction_method !== "string" ||
    value.extraction_method.length === 0 ||
    !Array.isArray(value.source_files) ||
    !value.source_files.every((file) => typeof file === "string") ||
    typeof value.curriculum_model !== "string" ||
    value.curriculum_model.length === 0 ||
    typeof value.structure_status !== "string" ||
    value.structure_status.length === 0 ||
    !Array.isArray(value.sections) ||
    !value.sections.every(isSection) ||
    !hasUniqueIdentifiers(value.sections) ||
    !Array.isArray(value.strands) ||
    !value.strands.every(isStrand) ||
    !hasUniqueIdentifiers(value.strands) ||
    !Array.isArray(value.nodes) ||
    !value.nodes.every(isNode) ||
    !hasUniqueCodes(value.nodes)
  ) {
    return false;
  }
  const sectionIdentifiers = new Set(value.sections.map((section) => section.identifier));
  if (
    !value.sections.every(
      (section) =>
        section.parent_identifier === null || sectionIdentifiers.has(section.parent_identifier),
    ) ||
    !value.nodes.every(
      (node) =>
        node.curriculum_path.every((identifier) => sectionIdentifiers.has(identifier)) &&
        (node.section_identifier === null ||
          (sectionIdentifiers.has(node.section_identifier) &&
            node.curriculum_path.includes(node.section_identifier))),
    )
  ) {
    return false;
  }
  const strandIdentifiers = new Set(value.strands.map((strand) => strand.identifier));
  return value.nodes.every(
    (node) => node.strand_identifier === null || strandIdentifiers.has(node.strand_identifier),
  );
};

export async function getCurriculumDetail(
  path: string,
  externalSignal?: AbortSignal,
  fetcher: typeof fetch = fetch,
): Promise<CurriculumDetail> {
  const timeoutSignal = AbortSignal.timeout(detailTimeoutMilliseconds);
  const signal =
    externalSignal === undefined ? timeoutSignal : AbortSignal.any([externalSignal, timeoutSignal]);
  const response = await fetcher(path, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) throw new Error(`curriculum detail returned ${String(response.status)}`);
  const payload: unknown = await response.json();
  if (!isDetail(payload)) throw new Error("curriculum detail returned an invalid payload");
  return payload;
}
