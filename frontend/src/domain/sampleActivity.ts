import { countryProfiles, type Country, type Role } from "./planner";

type PublicSampleProfile = {
  readonly level: string;
  readonly subject: string;
  readonly questions: readonly string[];
  readonly answers: readonly string[];
  readonly provenance: string;
};

export type SampleActivity = PublicSampleProfile & {
  readonly title: string;
  readonly country: string;
  readonly authority: string;
  readonly roleGuidance: string;
};

const provenance = "Illustrative GapSense sample; not curriculum-aligned or educator-reviewed.";

export const publicSampleProfiles: Readonly<Record<Country, PublicSampleProfile>> = {
  ghana: {
    level: "Basic 3",
    subject: "Science",
    questions: [
      "Name one source of light.",
      "Which sense do we use to hear sounds?",
      "Name one thing a plant needs to grow.",
      "Is water a solid, liquid, or gas at room temperature?",
      "Name one animal that lives in your community.",
    ],
    answers: [
      "The sun, a lamp, or another reasonable source",
      "Hearing",
      "Water, light, air, or another reasonable need",
      "Liquid",
      "Any locally familiar animal",
    ],
    provenance,
  },
  uganda: {
    level: "Primary 2",
    subject: "Mathematics",
    questions: [
      "Write the number that comes immediately after 19.",
      "Amina has 7 mangoes and receives 5 more. How many mangoes does she have now?",
      "Circle the greater number: 34 or 43.",
      "Share 12 pencils equally between 3 learners. How many does each learner get?",
      "Complete the pattern: 2, 4, 6, __, __.",
    ],
    answers: ["20", "12", "43", "4", "8, 10"],
    provenance,
  },
};

const roleGuidance: Readonly<Record<Role, string>> = {
  teacher:
    "For classroom exploration: review every item for local fit before using it with a class.",
  caregiver:
    "For home support: read the prompts aloud when useful and discuss the learner's approach.",
  learner:
    "For independent practice: work at your own pace and ask a trusted adult when a prompt is unclear.",
  tutor:
    "For a support session: observe the learner's strategy and adapt the discussion without deficit labels.",
};

export function buildSampleActivity(role: Role, country: Country): SampleActivity {
  const profile = publicSampleProfiles[country];
  const countryProfile = countryProfiles[country];
  return {
    ...profile,
    title: `${countryProfile.name} ${profile.level} ${profile.subject} sample`,
    country: countryProfile.name,
    authority: countryProfile.authority,
    roleGuidance: roleGuidance[role],
  };
}
