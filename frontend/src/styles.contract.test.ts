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

  it("carries the full GapSense palette through every public journey", () => {
    expect(stylesheet).toMatch(
      /\.planner::before[\s\S]*var\(--green\)[\s\S]*var\(--gold\)[\s\S]*var\(--coral\)/,
    );
    expect(stylesheet).toMatch(
      /\.choice-group:nth-of-type\(1\) \.step-number[\s\S]*var\(--green\)/,
    );
    expect(stylesheet).toMatch(/\.choice-group:nth-of-type\(2\) \.step-number[\s\S]*var\(--gold\)/);
    expect(stylesheet).toMatch(
      /\.choice-group:nth-of-type\(3\) \.step-number[\s\S]*var\(--coral\)/,
    );
    expect(stylesheet).toMatch(/\.countries[\s\S]*var\(--gold-rgb\)[\s\S]*var\(--coral-rgb\)/);
    expect(stylesheet).toMatch(
      /\.page-shell--curriculum[\s\S]*var\(--green-rgb\)[\s\S]*var\(--gold-rgb\)/,
    );
    expect(stylesheet).toMatch(/\.trust-grid article:nth-child\(1\)[\s\S]*var\(--green-wash\)/);
    expect(stylesheet).toMatch(/\.trust-grid article:nth-child\(2\)[\s\S]*var\(--gold-wash\)/);
    expect(stylesheet).toMatch(/\.trust-grid article:nth-child\(3\)[\s\S]*var\(--coral-wash\)/);
    expect(stylesheet).toMatch(
      /\.assessment-workspace[\s\S]*var\(--gold-rgb\)[\s\S]*var\(--coral-rgb\)/,
    );
    expect(stylesheet).toContain(".page-shell--not-found");
  });

  it("provides accessible light and dark semantic tokens for the appearance switcher", () => {
    expect(stylesheet).toContain('[data-theme="dark"]');
    expect(stylesheet).toMatch(/\[data-theme="dark"\][\s\S]*--paper:[\s\S]*--surface:/);
    expect(stylesheet).toMatch(/\[data-theme="dark"\][\s\S]*--green:[\s\S]*--gold:[\s\S]*--coral:/);
    expect(stylesheet).toContain(".theme-switcher");
    expect(stylesheet).toMatch(
      /\.theme-switcher input:focus-visible \+ span[\s\S]*outline:\s*3px solid var\(--focus\)/,
    );
    expect(stylesheet).toMatch(/@media print[\s\S]*\.theme-control[\s\S]*display:\s*none/);
  });

  it("does not replace theme-aware controls with a hard-coded high-contrast colour", () => {
    const highContrastRules = stylesheet.slice(
      stylesheet.indexOf("@media (prefers-contrast: more)"),
      stylesheet.indexOf("@media print"),
    );

    expect(highContrastRules).toContain("--line:");
    expect(highContrastRules).not.toMatch(/\.button[\s\S]*background:\s*#/);
  });

  it("keeps selected themes and disabled actions identifiable without colour", () => {
    expect(stylesheet).toMatch(/\.theme-switcher input:checked \+ span::after[\s\S]*opacity:\s*1/);
    expect(stylesheet).toMatch(
      /@media \(forced-colors: active\)[\s\S]*\.theme-switcher input:checked \+ span/,
    );
    expect(stylesheet).toMatch(
      /@media \(forced-colors: active\)[\s\S]*\.button:disabled[\s\S]*border-style:\s*dashed/,
    );
  });

  it("uses a clear compact theme control and denser cards at supported phone widths", () => {
    expect(stylesheet).toMatch(/\.theme-select[\s\S]*display:\s*none/);
    expect(stylesheet).toMatch(
      /@media \(max-width: 38rem\)[\s\S]*\.theme-switcher[\s\S]*display:\s*none[\s\S]*\.theme-select[\s\S]*display:\s*block/,
    );
    expect(stylesheet).toMatch(
      /@media \(min-width: 23rem\) and \(max-width: 46rem\)[\s\S]*\.choice-grid--roles[\s\S]*repeat\(2/,
    );
    expect(stylesheet).toMatch(
      /@media \(min-width: 23rem\) and \(max-width: 46rem\)[\s\S]*\.choice-grid--goals[\s\S]*repeat\(2/,
    );
    expect(stylesheet).toMatch(
      /\.choice-card__body,[\s\S]*\.country-choice__body[\s\S]*height:\s*100%/,
    );
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
