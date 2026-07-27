import { describe, expect, it } from "vitest";

import { buildAssessmentDocument } from "./assessmentDocument";

describe("buildAssessmentDocument", () => {
  it("creates a self-contained escaped document with questions and answers", () => {
    const html = buildAssessmentDocument({
      title: "Science <practice>",
      country: "Ghana",
      authority: "NaCCA",
      level: "Basic 3",
      subject: "Science",
      questions: ["What does A & B mean?", "Second question"],
      answers: ["Use <example>"],
    });

    expect(html).toContain("Science &lt;practice&gt;");
    expect(html).toContain("What does A &amp; B mean?");
    expect(html).toContain("Answer guidance: Use &lt;example&gt;");
    expect(html).toContain("Answer guidance: Review with an educator");
    expect(html).toContain(
      "Illustrative GapSense sample; not curriculum-aligned or educator-reviewed.",
    );
    expect(html).not.toContain("Local prototype");
  });
});
