import type { Country, Goal, Role } from "./planner";

export type SampleDraft = {
  readonly role: Role | null;
  readonly country: Country | null;
  readonly goal: Goal | null;
  readonly reviewed: boolean;
};

export type SampleDraftRecovery = "empty" | "restored" | "discarded" | "unavailable";

export type DraftStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export const sampleDraftStorageKey = "gapsense:sample-draft:v1";

export const initialSampleDraft: SampleDraft = {
  role: null,
  country: null,
  goal: null,
  reviewed: false,
};

const roles: readonly Role[] = ["teacher", "caregiver", "learner", "tutor"];
const countries: readonly Country[] = ["ghana", "uganda"];
const restorableGoals: readonly Goal[] = ["practice"];

const isRole = (value: unknown): value is Role =>
  typeof value === "string" && roles.includes(value as Role);

const isCountry = (value: unknown): value is Country =>
  typeof value === "string" && countries.includes(value as Country);

const isGoal = (value: unknown): value is Goal =>
  typeof value === "string" && restorableGoals.includes(value as Goal);

const decodeSampleDraft = (value: unknown): SampleDraft | null => {
  if (typeof value !== "object" || value === null) return null;
  const candidate = value as Record<string, unknown>;
  if (candidate.version !== 1 && candidate.version !== 2) return null;
  const role = candidate.role;
  const country = candidate.country;
  const goal = candidate.version === 1 ? "practice" : candidate.goal;
  const reviewed = candidate.reviewed;
  if (role !== null && !isRole(role)) return null;
  if (country !== null && !isCountry(country)) return null;
  if (goal !== null && !isGoal(goal)) return null;
  if (typeof reviewed !== "boolean") return null;
  if (reviewed && !(isRole(role) && isCountry(country) && isGoal(goal))) return null;
  return { role, country, goal, reviewed };
};

export function clearSampleDraft(storage: DraftStorage): void {
  try {
    storage.removeItem(sampleDraftStorageKey);
  } catch {
    return;
  }
}

export function readSampleDraft(storage: DraftStorage): {
  readonly draft: SampleDraft;
  readonly recovery: SampleDraftRecovery;
} {
  let stored: string | null;
  try {
    stored = storage.getItem(sampleDraftStorageKey);
  } catch {
    return { draft: initialSampleDraft, recovery: "unavailable" };
  }
  if (stored === null) return { draft: initialSampleDraft, recovery: "empty" };

  try {
    const value: unknown = JSON.parse(stored);
    const draft = decodeSampleDraft(value);
    if (draft === null) {
      clearSampleDraft(storage);
      return { draft: initialSampleDraft, recovery: "discarded" };
    }
    return {
      draft,
      recovery: "restored",
    };
  } catch {
    clearSampleDraft(storage);
    return { draft: initialSampleDraft, recovery: "discarded" };
  }
}

export function saveSampleDraft(storage: DraftStorage, draft: SampleDraft): boolean {
  try {
    storage.setItem(
      sampleDraftStorageKey,
      JSON.stringify({
        version: 2,
        role: draft.role,
        country: draft.country,
        goal: draft.goal,
        reviewed: draft.reviewed,
      }),
    );
    return true;
  } catch {
    return false;
  }
}
