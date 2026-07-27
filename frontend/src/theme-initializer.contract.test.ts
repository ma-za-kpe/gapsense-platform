/// <reference types="node" />

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const index = readFileSync(resolve(process.cwd(), "index.html"), "utf8");
const initializer = readFileSync(resolve(process.cwd(), "public/theme-init.js"), "utf8");

describe("first-paint theme initializer", () => {
  it("runs the external same-origin initializer before the React application", () => {
    const initializerPosition = index.indexOf('<script src="/theme-init.js"></script>');
    const applicationPosition = index.indexOf(
      '<script type="module" src="/src/main.tsx"></script>',
    );

    expect(initializerPosition).toBeGreaterThan(0);
    expect(applicationPosition).toBeGreaterThan(initializerPosition);
    expect(index).toContain('<meta name="color-scheme" content="light dark" />');
  });

  it("uses the same allowlisted storage and system-preference contract", () => {
    expect(initializer).toContain("gapsense.theme-preference.v1");
    expect(initializer).toContain("prefers-color-scheme: dark");
    expect(initializer).toContain("dataset.theme = resolved");
    expect(initializer).toContain("dataset.themePreference = preference");
    expect(initializer).not.toMatch(/account|learner|school|answer/i);
  });
});
