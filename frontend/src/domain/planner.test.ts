import { describe, expect, it } from "vitest";

import {
  countryProfiles,
  goalProfiles,
  initialPlan,
  isPlanComplete,
  plannerReducer,
  type PlannerState,
} from "./planner";

describe("assessment planner domain", () => {
  const roles = ["teacher", "caregiver", "learner", "tutor"] as const;
  const countries = ["ghana", "uganda"] as const;

  it("starts anonymous and incomplete", () => {
    expect(initialPlan).toEqual({ role: null, country: null, goal: null, reviewed: false });
    expect(isPlanComplete(initialPlan)).toBe(false);
  });

  it.each([
    { role: null, country: "ghana", goal: "practice", reviewed: false },
    { role: "teacher", country: null, goal: "practice", reviewed: false },
    { role: "teacher", country: "ghana", goal: null, reviewed: false },
  ] satisfies readonly PlannerState[])(
    "stays incomplete until all three meaningful choices exist",
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
    const goalSelected = plannerReducer(countrySelected, {
      type: "select-goal",
      goal: "practice",
    });
    const reviewed = plannerReducer(goalSelected, { type: "review" });

    expect(reviewed).toEqual({
      role: "teacher",
      country: "ghana",
      goal: "practice",
      reviewed: true,
    });
    expect(isPlanComplete(reviewed)).toBe(true);
  });

  it("reviews every supported role and country combination deterministically", () => {
    for (const role of roles) {
      for (const country of countries) {
        const selectedRole = plannerReducer(initialPlan, { type: "select-role", role });
        const selectedCountry = plannerReducer(selectedRole, {
          type: "select-country",
          country,
        });
        const selectedGoal = plannerReducer(selectedCountry, {
          type: "select-goal",
          goal: "practice",
        });
        expect(plannerReducer(selectedGoal, { type: "review" })).toEqual({
          role,
          country,
          goal: "practice",
          reviewed: true,
        });
      }
    }
  });

  it("invalidates review after every editable choice and ignores locked goals", () => {
    const reviewed: PlannerState = {
      role: "teacher",
      country: "ghana",
      goal: "practice",
      reviewed: true,
    };

    expect(plannerReducer(reviewed, { type: "select-role", role: "tutor" }).reviewed).toBe(false);
    expect(plannerReducer(reviewed, { type: "select-country", country: "uganda" }).reviewed).toBe(
      false,
    );
    expect(plannerReducer(reviewed, { type: "select-goal", goal: "practice" }).reviewed).toBe(
      false,
    );
    expect(plannerReducer(reviewed, { type: "select-goal", goal: "diagnostic" })).toBe(reviewed);
    expect(plannerReducer(reviewed, { type: "select-goal", goal: "assessment" })).toBe(reviewed);
  });

  it("resets an in-progress plan", () => {
    const state: PlannerState = {
      role: "caregiver",
      country: "uganda",
      goal: "practice",
      reviewed: true,
    };

    expect(plannerReducer(state, { type: "reset" })).toEqual(initialPlan);
  });

  it("keeps the complete product intent visible without claiming unavailable workflows", () => {
    expect(goalProfiles.practice).toMatchObject({
      label: "Practice activity",
      available: true,
    });
    expect(goalProfiles.diagnostic).toMatchObject({
      label: "Diagnostic pathway",
      available: false,
      status: "In development",
    });
    expect(goalProfiles.assessment).toMatchObject({
      label: "Assessment package",
      available: false,
      status: "Requires reviewed evidence",
    });
    expect(plannerReducer(initialPlan, { type: "select-goal", goal: "diagnostic" })).toBe(
      initialPlan,
    );
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
