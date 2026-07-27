export type Role = "teacher" | "caregiver" | "learner" | "tutor";
export type Country = "ghana" | "uganda";

export type PlannerState = {
  readonly role: Role | null;
  readonly country: Country | null;
  readonly reviewed: boolean;
};

export type CompletePlannerState = PlannerState & {
  readonly role: Role;
  readonly country: Country;
  readonly reviewed: true;
};

export type PlannerAction =
  | { readonly type: "select-role"; readonly role: Role }
  | { readonly type: "select-country"; readonly country: Country }
  | { readonly type: "review" }
  | { readonly type: "reset" };

export type CountryProfile = {
  readonly name: string;
  readonly authority: string;
  readonly authorityLongName: string;
  readonly levels: readonly string[];
  readonly readiness: "inventory-in-progress";
  readonly accent: string;
};

export const initialPlan: PlannerState = {
  role: null,
  country: null,
  reviewed: false,
};

export const roleProfiles: Readonly<
  Record<Role, { readonly label: string; readonly note: string }>
> = {
  teacher: { label: "Teacher", note: "Plan for a class or learning group" },
  caregiver: { label: "Parent or caregiver", note: "Support learning beyond the classroom" },
  learner: { label: "Learner", note: "Practise independently at your pace" },
  tutor: { label: "Tutor", note: "Prepare focused support sessions" },
};

export const countryProfiles: Readonly<Record<Country, CountryProfile>> = {
  ghana: {
    name: "Ghana",
    authority: "NaCCA",
    authorityLongName: "National Council for Curriculum and Assessment",
    levels: ["KG", "Basic 1–3", "Basic 4–6", "JHS (Basic 7–9)", "SHS"],
    readiness: "inventory-in-progress",
    accent: "gold",
  },
  uganda: {
    name: "Uganda",
    authority: "NCDC",
    authorityLongName: "National Curriculum Development Centre",
    levels: ["Early Childhood", "Primary 1–3", "Primary 4–7", "O-Level (S1–S4)", "A-Level (S5–S6)"],
    readiness: "inventory-in-progress",
    accent: "coral",
  },
};

export function isPlanComplete(state: PlannerState): state is CompletePlannerState {
  return state.role !== null && state.country !== null;
}

export function plannerReducer(state: PlannerState, action: PlannerAction): PlannerState {
  switch (action.type) {
    case "select-role":
      return { ...state, role: action.role, reviewed: false };
    case "select-country":
      return { ...state, country: action.country, reviewed: false };
    case "review":
      return isPlanComplete(state) ? { ...state, reviewed: true } : state;
    case "reset":
      return initialPlan;
  }
}
