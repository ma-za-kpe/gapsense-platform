import { describe, expect, it } from "vitest";

import { buildSampleActivity, publicSampleProfiles } from "./sampleActivity";

describe("truthful public sample activities", () => {
  it("uses one explicit, distinct illustrative context per country", () => {
    const ghana = buildSampleActivity("teacher", "ghana");
    const uganda = buildSampleActivity("teacher", "uganda");

    expect(ghana).toMatchObject({
      country: "Ghana",
      authority: "NaCCA",
      level: "Basic 3",
      subject: "Science",
      title: "Ghana Basic 3 Science sample",
    });
    expect(uganda).toMatchObject({
      country: "Uganda",
      authority: "NCDC",
      level: "Primary 2",
      subject: "Mathematics",
      title: "Uganda Primary 2 Mathematics sample",
    });
    expect(ghana.questions).not.toEqual(uganda.questions);
    expect(ghana.questions).toHaveLength(ghana.answers.length);
    expect(uganda.questions).toHaveLength(uganda.answers.length);
  });

  it("makes the selected role change the practical guidance", () => {
    const guidance = (["teacher", "caregiver", "learner", "tutor"] as const).map(
      (role) => buildSampleActivity(role, "ghana").roleGuidance,
    );

    expect(new Set(guidance).size).toBe(4);
    expect(guidance[0]).toMatch(/classroom/i);
    expect(guidance[1]).toMatch(/home/i);
    expect(guidance[2]).toMatch(/your own pace/i);
    expect(guidance[3]).toMatch(/support session/i);
  });

  it("keeps every unsupported curriculum and diagnosis claim out of the sample contract", () => {
    for (const profile of Object.values(publicSampleProfiles)) {
      expect(profile.provenance).toBe(
        "Illustrative GapSense sample; not curriculum-aligned or educator-reviewed.",
      );
      expect(JSON.stringify(profile)).not.toMatch(/diagnos|confidence|earliest gap/i);
    }
  });
});
