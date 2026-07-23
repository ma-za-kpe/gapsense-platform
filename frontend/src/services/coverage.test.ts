import { describe, expect, it, vi } from "vitest";

import { getCurriculumCoverage } from "./coverage";

const validCoveragePayload = {
  repository_status: "available",
  complete: false,
  warnings: ["review_state_not_complete"],
  countries: [
    {
      code: "GH",
      name: "Ghana",
      authority: "National Council for Curriculum and Assessment (NaCCA)",
      authority_url: "https://nacca.gov.gh/curriculum/",
      availability: "present_unverified",
      review_status: "not_verified",
      repository_file_count: 3,
      levels: [
        {
          identifier: "lower_primary",
          name: "Lower Primary",
          official_phase: "Key Phase 2 (Basic 1–3)",
          review_status: "not_verified",
        },
      ],
    },
    {
      code: "UG",
      name: "Uganda",
      authority: "National Curriculum Development Centre (NCDC)",
      authority_url: "https://ncdc.go.ug/directorates/",
      availability: "missing",
      review_status: "not_verified",
      repository_file_count: 0,
      levels: [
        {
          identifier: "lower_secondary",
          name: "Lower Secondary",
          official_phase: "UCE cycle",
          review_status: "not_verified",
        },
      ],
    },
  ],
} as const;

describe("curriculum coverage client", () => {
  it("accepts the typed incomplete-coverage contract", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(validCoveragePayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(getCurriculumCoverage(fetcher)).resolves.toEqual(validCoveragePayload);
    expect(fetcher).toHaveBeenCalledOnce();
    const call = fetcher.mock.calls.at(0);
    expect(call?.[0]).toBe("/api/v1/curriculum/coverage");
    expect(call?.[1]?.headers).toEqual({ Accept: "application/json" });
    expect(call?.[1]?.signal).toBeInstanceOf(AbortSignal);
  });

  it("fails closed on an unsuccessful response", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 503 }));

    await expect(getCurriculumCoverage(fetcher)).rejects.toThrow("coverage endpoint returned 503");
  });

  it.each([
    null,
    {},
    { ...validCoveragePayload, complete: true },
    { ...validCoveragePayload, repository_status: "complete" },
    { ...validCoveragePayload, warnings: "none" },
    { ...validCoveragePayload, countries: {} },
    { ...validCoveragePayload, countries: [null] },
    {
      ...validCoveragePayload,
      countries: [{ ...validCoveragePayload.countries[0], code: "KE" }],
    },
    {
      ...validCoveragePayload,
      countries: [{ ...validCoveragePayload.countries[0], repository_file_count: -1 }],
    },
    {
      ...validCoveragePayload,
      countries: [{ ...validCoveragePayload.countries[0], levels: [null] }],
    },
    {
      ...validCoveragePayload,
      countries: [
        { ...validCoveragePayload.countries[0], name: "Uganda" },
        validCoveragePayload.countries[1],
      ],
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          levels: [
            validCoveragePayload.countries[0].levels[0],
            validCoveragePayload.countries[0].levels[0],
          ],
        },
        validCoveragePayload.countries[1],
      ],
    },
    {
      ...validCoveragePayload,
      countries: [
        validCoveragePayload.countries[0],
        { ...validCoveragePayload.countries[1], levels: [] },
      ],
    },
  ])("fails closed on malformed payload %#", async (payload) => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));

    await expect(getCurriculumCoverage(fetcher)).rejects.toThrow(
      "coverage endpoint returned an invalid payload",
    );
  });
});
