import { describe, expect, it } from "vitest";

import { buildAssessmentDocument } from "./assessmentDocument";

describe("buildAssessmentDocument", () => {
  const input = {
    title: "Science <practice>",
    country: "Ghana",
    authority: "NaCCA",
    level: "Basic 3",
    subject: "Science",
    questions: ["What does A & B mean?", "Second question"],
    answers: ["Use <example>"],
  } as const;

  it("creates a learner worksheet without exposing answer guidance", () => {
    const html = buildAssessmentDocument(input, "learner");

    expect(html).toContain("Learner worksheet");
    expect(html).toContain("Science &lt;practice&gt;");
    expect(html).toContain("What does A &amp; B mean?");
    expect(html).not.toContain("Use &lt;example&gt;");
    expect(html).not.toContain("Review with an educator");
    expect(html).not.toContain("Answer guidance");
    expect(html).toContain(
      "Illustrative GapSense sample; not curriculum-aligned or educator-reviewed.",
    );
  });

  it("creates a separately labelled escaped answer guide", () => {
    const html = buildAssessmentDocument(input, "answer-guide");

    expect(html).toContain("Answer guide");
    expect(html).toContain("Science &lt;practice&gt;");
    expect(html).toContain("What does A &amp; B mean?");
    expect(html).toContain("Answer guidance: Use &lt;example&gt;");
    expect(html).toContain("Answer guidance: Review with an educator");
    expect(html).not.toContain("Local prototype");
  });
});
