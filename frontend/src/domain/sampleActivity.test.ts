import { describe, expect, it } from "vitest";

import { buildSampleActivity, publicSampleProfiles } from "./sampleActivity";

describe("truthful public sample activities", () => {
  const roles = ["teacher", "caregiver", "learner", "tutor"] as const;
  const countries = ["ghana", "uganda"] as const;

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
    const guidance = roles.map((role) => buildSampleActivity(role, "ghana").roleGuidance);

    expect(new Set(guidance).size).toBe(4);
    expect(guidance[0]).toMatch(/classroom/i);
    expect(guidance[1]).toMatch(/home/i);
    expect(guidance[2]).toMatch(/your own pace/i);
    expect(guidance[3]).toMatch(/support session/i);
  });

  it("builds all eight role-country samples with complete paired questions and answers", () => {
    for (const role of roles) {
      for (const country of countries) {
        const activity = buildSampleActivity(role, country);
        expect(activity.title).toContain(activity.country);
        expect(activity.authority).toMatch(/NaCCA|NCDC/);
        expect(activity.questions.length).toBeGreaterThan(0);
        expect(activity.questions).toHaveLength(activity.answers.length);
        expect(activity.questions.every((question) => question.trim().length > 0)).toBe(true);
        expect(activity.answers.every((answer) => answer.trim().length > 0)).toBe(true);
        expect(activity.roleGuidance.trim().length).toBeGreaterThan(0);
      }
    }
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
