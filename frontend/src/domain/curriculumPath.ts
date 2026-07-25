import type { Country } from "./planner";

const apiLevel = (country: Country, selected: string): string => {
  if (country === "ghana") {
    if (/Basic [1-3]/.test(selected)) return "lower_primary";
    if (/Basic [4-6]/.test(selected)) return "upper_primary";
    return selected.startsWith("JHS") ? "junior_high" : "senior_high";
  }
  if (/Primary [1-3]/.test(selected)) return "primary_1_3";
  if (selected.startsWith("Primary")) return "primary_4_7";
  return selected.startsWith("O-Level") ? "lower_secondary" : "upper_secondary";
};

const apiSubject = (selected: string): string =>
  selected === "English Language"
    ? "english"
    : selected === "General Science"
      ? "general_science"
      : selected.toLowerCase();

const apiPhase = (country: Country, selected: string): string => {
  const level = apiLevel(country, selected);
  return level.includes("high") || level.includes("secondary") ? "secondary" : "primary";
};

export const curriculumApiPath = (country: Country, selected: string, subject: string): string =>
  `/api/v1/curriculum/${country}/${apiPhase(country, selected)}/${apiLevel(country, selected)}/${apiSubject(subject)}`;
