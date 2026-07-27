import type { Country, Role } from "./planner";

export type SampleDraft = {
  readonly role: Role | null;
  readonly country: Country | null;
  readonly reviewed: boolean;
};

export type SampleDraftRecovery = "empty" | "restored" | "discarded" | "unavailable";

export type DraftStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export const sampleDraftStorageKey = "gapsense:sample-draft:v1";

export const initialSampleDraft: SampleDraft = {
  role: null,
  country: null,
  reviewed: false,
};

const roles: readonly Role[] = ["teacher", "caregiver", "learner", "tutor"];
const countries: readonly Country[] = ["ghana", "uganda"];

const isRole = (value: unknown): value is Role =>
  typeof value === "string" && roles.includes(value as Role);

const isCountry = (value: unknown): value is Country =>
  typeof value === "string" && countries.includes(value as Country);

const isSampleDraft = (value: unknown): value is SampleDraft => {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  if (candidate.version !== 1) return false;
  const role = candidate.role;
  const country = candidate.country;
  const reviewed = candidate.reviewed;
  if (role !== null && !isRole(role)) return false;
  if (country !== null && !isCountry(country)) return false;
  if (typeof reviewed !== "boolean") return false;
  return !reviewed || (isRole(role) && isCountry(country));
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
    if (!isSampleDraft(value)) {
      clearSampleDraft(storage);
      return { draft: initialSampleDraft, recovery: "discarded" };
    }
    return {
      draft: {
        role: value.role,
        country: value.country,
        reviewed: value.reviewed,
      },
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
        version: 1,
        role: draft.role,
        country: draft.country,
        reviewed: draft.reviewed,
      }),
    );
    return true;
  } catch {
    return false;
  }
}
