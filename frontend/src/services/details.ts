const detailTimeoutMilliseconds = 5_000;

export type CurriculumIndicator = {
  readonly code: string;
  readonly title: string;
  readonly question_type: string | null;
  readonly difficulty: number | null;
  readonly misconception_count: number;
};

export type CurriculumNode = {
  readonly code: string;
  readonly title: string;
  readonly content_standard: string;
  readonly prerequisites: readonly string[];
  readonly indicators: readonly CurriculumIndicator[];
};

export type CurriculumStrand = {
  readonly identifier: string;
  readonly name: string;
  readonly sub_strands: readonly string[];
};

export type CurriculumDetail = {
  readonly country: string;
  readonly phase: string;
  readonly level: string;
  readonly subject: string;
  readonly evidence_scope: "level" | "phase_only";
  readonly extraction_status: "located" | "extracted";
  readonly source_files: readonly string[];
  readonly strands: readonly CurriculumStrand[];
  readonly nodes: readonly CurriculumNode[];
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const isDetail = (value: unknown): value is CurriculumDetail => {
  if (!isRecord(value)) return false;
  return (
    typeof value.country === "string" &&
    typeof value.phase === "string" &&
    typeof value.level === "string" &&
    typeof value.subject === "string" &&
    (value.evidence_scope === "level" || value.evidence_scope === "phase_only") &&
    (value.extraction_status === "located" || value.extraction_status === "extracted") &&
    Array.isArray(value.source_files) &&
    value.source_files.every((file) => typeof file === "string") &&
    Array.isArray(value.strands) &&
    Array.isArray(value.nodes)
  );
};

export async function getCurriculumDetail(
  path: string,
  fetcher: typeof fetch = fetch,
): Promise<CurriculumDetail> {
  const response = await fetcher(path, {
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(detailTimeoutMilliseconds),
  });
  if (!response.ok) throw new Error(`curriculum detail returned ${String(response.status)}`);
  const payload: unknown = await response.json();
  if (!isDetail(payload)) throw new Error("curriculum detail returned an invalid payload");
  return payload;
}
