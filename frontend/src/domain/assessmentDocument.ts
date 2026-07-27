export type AssessmentDocumentInput = {
  readonly title: string;
  readonly country: string;
  readonly authority: string;
  readonly level: string;
  readonly subject: string;
  readonly questions: readonly string[];
  readonly answers: readonly string[];
};

const escapeHtml = (value: string): string =>
  value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");

export function buildAssessmentDocument(input: AssessmentDocumentInput): string {
  const questions = input.questions
    .map(
      (question, index) =>
        `<li>${escapeHtml(question)}<div class="answer-line"></div><small>Answer guidance: ${escapeHtml(input.answers[index] ?? "Review with an educator")}</small></li>`,
    )
    .join("");
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${escapeHtml(input.title)}</title><style>body{font-family:Arial,sans-serif;max-width:760px;margin:2rem auto;line-height:1.5}h1{margin-bottom:.25rem}.meta{color:#445}.answer-line{height:2rem;border-bottom:1px solid #999;margin:.5rem 0 1rem}small{display:block;color:#445}</style></head><body><p class="meta">GapSense · ${escapeHtml(input.country)} · ${escapeHtml(input.authority)}</p><h1>${escapeHtml(input.title)}</h1><p class="meta">${escapeHtml(input.level)} · ${escapeHtml(input.subject)}</p><ol>${questions}</ol><p class="meta">Illustrative GapSense sample; not curriculum-aligned or educator-reviewed.</p></body></html>`;
}
