import { describe, expect, it } from "vitest";

import {
  countryProfiles,
  initialPlan,
  isPlanComplete,
  plannerReducer,
  type PlannerState,
} from "./planner";

describe("assessment planner domain", () => {
  it("starts anonymous and incomplete", () => {
    expect(initialPlan).toEqual({ role: null, country: null, reviewed: false });
    expect(isPlanComplete(initialPlan)).toBe(false);
  });

  it.each([
    { role: null, country: "ghana", reviewed: false },
    { role: "teacher", country: null, reviewed: false },
  ] satisfies readonly PlannerState[])(
    "stays incomplete until both meaningful choices exist",
    (state) => {
      expect(isPlanComplete(state)).toBe(false);
      expect(plannerReducer(state, { type: "review" })).toBe(state);
    },
  );

  it("updates every choice and becomes complete", () => {
    const roleSelected = plannerReducer(initialPlan, { type: "select-role", role: "teacher" });
    const countrySelected = plannerReducer(roleSelected, {
      type: "select-country",
      country: "ghana",
    });
    const reviewed = plannerReducer(countrySelected, { type: "review" });

    expect(reviewed).toEqual({
      role: "teacher",
      country: "ghana",
      reviewed: true,
    });
    expect(isPlanComplete(reviewed)).toBe(true);
  });

  it("resets an in-progress plan", () => {
    const state: PlannerState = {
      role: "caregiver",
      country: "uganda",
      reviewed: true,
    };

    expect(plannerReducer(state, { type: "reset" })).toEqual(initialPlan);
  });

  it("keeps country structures distinct and honest", () => {
    expect(countryProfiles.ghana).toMatchObject({
      name: "Ghana",
      authority: "NaCCA",
      readiness: "inventory-in-progress",
    });
    expect(countryProfiles.uganda).toMatchObject({
      name: "Uganda",
      authority: "NCDC",
      readiness: "inventory-in-progress",
    });
    expect(countryProfiles.ghana.levels).not.toEqual(countryProfiles.uganda.levels);
    expect(countryProfiles.ghana.levels).toContain("JHS (Basic 7–9)");
    expect(countryProfiles.ghana.levels).toContain("SHS");
    expect(countryProfiles.uganda.levels).toContain("O-Level (S1–S4)");
    expect(countryProfiles.uganda.levels).toContain("A-Level (S5–S6)");
  });
});
