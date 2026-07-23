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
    expect(initialPlan).toEqual({ role: null, country: null, goal: null, reviewed: false });
    expect(isPlanComplete(initialPlan)).toBe(false);
  });

  it.each([
    { role: "teacher", country: null, goal: null, reviewed: false },
    { role: "teacher", country: "ghana", goal: null, reviewed: false },
  ] satisfies readonly PlannerState[])(
    "stays incomplete until every required choice exists",
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
      goal: "diagnostic",
    });
    const reviewed = plannerReducer(goalSelected, { type: "review" });

    expect(reviewed).toEqual({
      role: "teacher",
      country: "ghana",
      goal: "diagnostic",
      reviewed: true,
    });
    expect(isPlanComplete(reviewed)).toBe(true);
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
  });
});
