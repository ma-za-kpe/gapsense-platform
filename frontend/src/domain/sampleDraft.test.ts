import { afterEach, describe, expect, it, vi } from "vitest";

import {
  clearSampleDraft,
  initialSampleDraft,
  readSampleDraft,
  sampleDraftStorageKey,
  saveSampleDraft,
} from "./sampleDraft";

afterEach(() => {
  window.localStorage.clear();
});

describe("versioned anonymous sample draft", () => {
  it("starts empty without inventing a selection", () => {
    expect(readSampleDraft(window.localStorage)).toEqual({
      draft: initialSampleDraft,
      recovery: "empty",
    });
  });

  it("round-trips only the non-PII choices needed to resume", () => {
    const draft = {
      role: "teacher",
      country: "ghana",
      goal: "practice",
      reviewed: true,
    } as const;

    expect(saveSampleDraft(window.localStorage, draft)).toBe(true);
    expect(readSampleDraft(window.localStorage)).toEqual({
      draft,
      recovery: "restored",
    });
    expect(window.localStorage.getItem(sampleDraftStorageKey)).toBe(
      '{"version":2,"role":"teacher","country":"ghana","goal":"practice","reviewed":true}',
    );
  });

  it("restores the former activity-only draft as an explicit practice goal", () => {
    window.localStorage.setItem(
      sampleDraftStorageKey,
      '{"version":1,"role":"teacher","country":"ghana","reviewed":true}',
    );

    expect(readSampleDraft(window.localStorage)).toEqual({
      draft: {
        role: "teacher",
        country: "ghana",
        goal: "practice",
        reviewed: true,
      },
      recovery: "restored",
    });
  });

  it.each([
    "{not-json",
    "null",
    "42",
    '{"version":3,"role":"teacher","country":"ghana","goal":"practice","reviewed":true}',
    '{"version":2,"role":"unknown","country":"ghana","goal":"practice","reviewed":true}',
    '{"version":2,"role":"teacher","country":"unknown","goal":"practice","reviewed":true}',
    '{"version":2,"role":"teacher","country":"ghana","goal":"unknown","reviewed":true}',
    '{"version":2,"role":"teacher","country":"ghana","goal":"diagnostic","reviewed":true}',
    '{"version":2,"role":null,"country":null,"goal":null,"reviewed":true}',
    '{"version":2,"role":42,"country":"ghana","goal":"practice","reviewed":false}',
    '{"version":2,"role":"teacher","country":42,"goal":"practice","reviewed":false}',
    '{"version":2,"role":"teacher","country":"ghana","goal":42,"reviewed":false}',
    '{"version":2,"role":"teacher","country":"ghana","goal":"practice","reviewed":"yes"}',
  ])("discards an unsafe or incompatible draft: %s", (value) => {
    window.localStorage.setItem(sampleDraftStorageKey, value);

    expect(readSampleDraft(window.localStorage)).toEqual({
      draft: initialSampleDraft,
      recovery: "discarded",
    });
    expect(window.localStorage.getItem(sampleDraftStorageKey)).toBeNull();
  });

  it("fails safely when browser storage is unavailable", () => {
    const storage = {
      getItem: vi.fn(() => {
        throw new DOMException("blocked");
      }),
      setItem: vi.fn(() => {
        throw new DOMException("full");
      }),
      removeItem: vi.fn(() => {
        throw new DOMException("blocked");
      }),
    };

    expect(readSampleDraft(storage)).toEqual({
      draft: initialSampleDraft,
      recovery: "unavailable",
    });
    expect(saveSampleDraft(storage, initialSampleDraft)).toBe(false);
    expect(() => clearSampleDraft(storage)).not.toThrow();
  });

  it("clears a restored draft for a safe restart", () => {
    expect(saveSampleDraft(window.localStorage, initialSampleDraft)).toBe(true);

    clearSampleDraft(window.localStorage);

    expect(window.localStorage.getItem(sampleDraftStorageKey)).toBeNull();
  });
});
