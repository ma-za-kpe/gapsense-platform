/// <reference types="node" />

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const stylesheet = readFileSync(resolve(process.cwd(), "src/styles.css"), "utf8");

describe("interface stylesheet contract", () => {
  it("defines every curriculum semantic token it consumes", () => {
    expect(stylesheet).toMatch(/--line-strong:\s*#[0-9a-f]{6}/i);
    expect(stylesheet).toMatch(/--wash:\s*#[0-9a-f]{6}/i);
    expect(stylesheet.match(/var\(--line-strong\)/g)?.length).toBeGreaterThan(0);
    expect(stylesheet.match(/var\(--wash\)/g)?.length).toBeGreaterThan(0);
  });

  it("preserves the documented GapSense colour families and country accents", () => {
    for (const token of [
      "--ink-950",
      "--paper-muted",
      "--green-600",
      "--gold-500",
      "--coral-500",
    ]) {
      expect(stylesheet).toContain(token);
    }
    expect(stylesheet).toMatch(
      /\.country-choice--gold \.country-choice__body[\s\S]*var\(--gold-100\)/,
    );
    expect(stylesheet).toMatch(
      /\.country-choice--coral \.country-choice__body[\s\S]*var\(--coral-100\)/,
    );
    expect(stylesheet).toMatch(/\.country-panel--gold[\s\S]*var\(--gold-100\)/);
    expect(stylesheet).toMatch(/\.country-panel--coral[\s\S]*var\(--coral-100\)/);
  });

  it("keeps the green and gold atmosphere of the established entry experience", () => {
    expect(stylesheet).toMatch(
      /\.hero[\s\S]*radial-gradient\([^;]*var\(--gold-rgb\)[^;]*radial-gradient\([^;]*var\(--green-rgb\)/,
    );
    expect(stylesheet).toMatch(/\.planner[\s\S]*var\(--green-100\)/);
  });

  it("does not hide the real curriculum route in compact navigation", () => {
    expect(stylesheet).not.toContain('a[href="#curriculum"]');
    expect(stylesheet).toContain(".mobile-nav");
  });

  it("keeps authored supporting text at or above fourteen pixels", () => {
    const undersizedRem = /font-size:\s*0\.(?:[0-7]\d?|8[0-6])rem/g;
    expect(stylesheet.match(undersizedRem)).toBeNull();
  });

  it("contains explicit touch-target and compact-page safeguards", () => {
    expect(stylesheet).toContain("--target-min: 2.75rem");
    expect(stylesheet).toMatch(/\.mobile-nav[\s\S]*min-height:\s*var\(--target-min\)/);
    expect(stylesheet).toMatch(/@media \(max-width: 38rem\)[\s\S]*\.hero-visual/);
  });

  it("styles the illustrative learning path as a responsive product model", () => {
    expect(stylesheet).toContain(".hero-visual");
    expect(stylesheet).toContain(".learning-map");
    expect(stylesheet).toContain(".map-node--root");
    expect(stylesheet).toContain(".learning-model-note");
  });

  it("keeps evidence provenance visible and answer guidance out of learner printing", () => {
    expect(stylesheet).toContain(".coverage-provenance");
    expect(stylesheet).toMatch(
      /@media print[\s\S]*\.answer-guidance[\s\S]*display:\s*none\s*!important/,
    );
  });
});
