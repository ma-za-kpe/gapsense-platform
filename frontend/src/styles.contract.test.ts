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
    expect(stylesheet).toMatch(/@media \(max-width: 38rem\)[\s\S]*\.hero-evidence/);
  });
});
