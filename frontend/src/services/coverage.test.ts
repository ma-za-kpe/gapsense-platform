import { describe, expect, it, vi } from "vitest";

import { getCurriculumCoverage } from "./coverage";

const validCoveragePayload = {
  repository_status: "available",
  complete: false,
  warnings: ["review_state_not_complete"],
  snapshot: {
    generated_at: "2026-07-27T17:00:00Z",
    source_version: "curriculum-2026-07-29-candidate.1",
    review_status: "not_verified",
  },
  catalog: {
    as_of: "2026-07-29",
    scope_status: "official_authority_inventory",
    represented_cells: 1,
    total_cells: 1,
    evidence_cells: 1,
  },
  source_inventory: {
    as_of: "2026-07-23",
    total_records: 1,
    acquired_artifacts: 0,
    records: [
      {
        identifier: "gh-jhs-official-index-current",
        country: "GH",
        phase: "secondary",
        level: "JHS1-JHS3",
        subject: "all",
        edition: "current index",
        source_url: "https://nacca.gov.gh/common-core-programme-ccp/",
        retrieved_on: "2026-07-23",
        license_status: "official_index_only_document_not_licensed_for_redistribution",
        artifact_available: false,
        artifact_pages: null,
        extraction_status: "index_only",
        review_status: "official_index_verified",
        known_gap: "Document records remain.",
      },
    ],
  },
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
          scope_note: "Official scope statement for Lower Primary.",
          review_status: "not_verified",
        },
      ],
      subjects: [
        {
          identifier: "mathematics",
          name: "Mathematics",
          phase: "primary",
          availability: "present_unverified",
          review_status: "not_verified",
        },
      ],
      coverage_matrix: [
        {
          level_identifier: "lower_primary",
          level_name: "Lower Primary",
          phase: "primary",
          subject_identifier: "mathematics",
          subject_name: "Mathematics",
          status: "extracted",
          evidence_scope: "level",
          source_url: "https://nacca.gov.gh/curriculum/",
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
          scope_note: "Official scope statement for Lower Secondary.",
          review_status: "not_verified",
        },
      ],
      subjects: [],
      coverage_matrix: [],
    },
  ],
} as const;

const sourceRecordWith = (overrides: Record<string, unknown>) => ({
  ...validCoveragePayload.source_inventory.records[0],
  ...overrides,
});

const sourceInventoryWith = (overrides: Record<string, unknown>) => ({
  ...validCoveragePayload.source_inventory,
  ...overrides,
});

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

  it("accepts reviewed release metadata", async () => {
    const payload = {
      ...validCoveragePayload,
      snapshot: { ...validCoveragePayload.snapshot, review_status: "human_reviewed" },
    };
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(getCurriculumCoverage(fetcher)).resolves.toEqual(payload);
  });

  it("accepts a partial release with an acquired Uganda source record", async () => {
    const sourceRecord = {
      ...validCoveragePayload.source_inventory.records[0],
      identifier: "ug-lower-secondary-mathematics",
      country: "UG",
      phase: "primary",
      source_url: "https://ncdc.go.ug/resource/lower-secondary-mathematics/",
      artifact_available: true,
      artifact_pages: 48,
      extraction_status: "normalized_projection_unverified",
    } as const;
    const payload = {
      ...validCoveragePayload,
      repository_status: "partial",
      source_inventory: {
        ...validCoveragePayload.source_inventory,
        acquired_artifacts: 1,
        records: [sourceRecord],
      },
    };
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(getCurriculumCoverage(fetcher)).resolves.toEqual(payload);
  });

  it("accepts an exact Uganda curriculum matrix cell", async () => {
    const payload = {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          availability: "missing",
          repository_file_count: 0,
          subjects: [],
          coverage_matrix: [],
        },
        {
          ...validCoveragePayload.countries[1],
          availability: "present_unverified",
          subjects: [
            {
              identifier: "mathematics",
              name: "Mathematics",
              phase: "secondary",
              availability: "present_unverified",
              review_status: "not_verified",
            },
          ],
          coverage_matrix: [
            {
              level_identifier: "lower_secondary",
              level_name: "Lower Secondary",
              phase: "secondary",
              subject_identifier: "mathematics",
              subject_name: "Mathematics",
              status: "extracted",
              evidence_scope: "level",
              source_url: "https://ncdc.go.ug/directorates/",
            },
          ],
        },
      ],
    };
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(getCurriculumCoverage(fetcher)).resolves.toEqual(payload);
  });

  it("accepts an unavailable release only with empty projections and null inventories", async () => {
    const payload = {
      ...validCoveragePayload,
      repository_status: "missing",
      catalog: null,
      source_inventory: null,
      snapshot: { ...validCoveragePayload.snapshot, source_version: null },
      countries: validCoveragePayload.countries.map((country) => ({
        ...country,
        availability: "missing",
        repository_file_count: 0,
        subjects: [],
        coverage_matrix: [],
      })),
    };
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(getCurriculumCoverage(fetcher)).resolves.toEqual(payload);
  });

  it("accepts an explicit missing subject record", async () => {
    const ghana = validCoveragePayload.countries[0];
    const payload = {
      ...validCoveragePayload,
      catalog: { ...validCoveragePayload.catalog, evidence_cells: 0 },
      countries: [
        {
          ...ghana,
          availability: "missing",
          repository_file_count: 0,
          subjects: [{ ...ghana.subjects[0], availability: "missing" }],
          coverage_matrix: [{ ...ghana.coverage_matrix[0], status: "missing" }],
        },
        validCoveragePayload.countries[1],
      ],
    };
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(getCurriculumCoverage(fetcher)).resolves.toEqual(payload);
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
    { ...validCoveragePayload, snapshot: null },
    {
      ...validCoveragePayload,
      snapshot: { ...validCoveragePayload.snapshot, generated_at: "soon" },
    },
    { ...validCoveragePayload, snapshot: { ...validCoveragePayload.snapshot, source_version: 1 } },
    {
      ...validCoveragePayload,
      snapshot: { ...validCoveragePayload.snapshot, review_status: "approved" },
    },
    {
      ...validCoveragePayload,
      repository_status: "missing",
    },
    { ...validCoveragePayload, catalog: null },
    {
      ...validCoveragePayload,
      catalog: { ...validCoveragePayload.catalog, as_of: 20260729 },
    },
    {
      ...validCoveragePayload,
      catalog: { ...validCoveragePayload.catalog, as_of: "today" },
    },
    {
      ...validCoveragePayload,
      catalog: { ...validCoveragePayload.catalog, scope_status: "complete" },
    },
    {
      ...validCoveragePayload,
      catalog: { ...validCoveragePayload.catalog, represented_cells: 0 },
    },
    {
      ...validCoveragePayload,
      catalog: { ...validCoveragePayload.catalog, represented_cells: 1.5 },
    },
    {
      ...validCoveragePayload,
      catalog: { ...validCoveragePayload.catalog, total_cells: "1" },
    },
    {
      ...validCoveragePayload,
      catalog: { ...validCoveragePayload.catalog, total_cells: 2 },
    },
    {
      ...validCoveragePayload,
      catalog: { ...validCoveragePayload.catalog, evidence_cells: "1" },
    },
    {
      ...validCoveragePayload,
      catalog: { ...validCoveragePayload.catalog, evidence_cells: -1 },
    },
    {
      ...validCoveragePayload,
      catalog: { ...validCoveragePayload.catalog, evidence_cells: 2 },
    },
    { ...validCoveragePayload, source_inventory: null },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({ as_of: 20260723 }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({ as_of: "today" }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({ total_records: 0 }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({ total_records: 1.5 }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({ acquired_artifacts: "0" }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({ acquired_artifacts: -1 }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({ records: {} }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({ records: [] }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({ records: [null] }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        as_of: "2026-07-22",
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ country: "KE" })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ phase: "tertiary" })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ identifier: 42 })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ level: 42 })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ subject: 42 })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ edition: 42 })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ source_url: 42 })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ retrieved_on: 42 })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ retrieved_on: "today" })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ license_status: "public_domain" })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ artifact_available: "yes" })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ artifact_pages: 0 })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ artifact_pages: true })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ artifact_pages: 48 })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ extraction_status: "complete" })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ review_status: 42 })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ review_status: "approved" })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ known_gap: 42 })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        records: [sourceRecordWith({ source_url: "https://example.com/" })],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({
        total_records: 2,
        records: [
          validCoveragePayload.source_inventory.records[0],
          validCoveragePayload.source_inventory.records[0],
        ],
      }),
    },
    {
      ...validCoveragePayload,
      source_inventory: sourceInventoryWith({ acquired_artifacts: 1 }),
    },
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
        {
          ...validCoveragePayload.countries[0],
          levels: [{ ...validCoveragePayload.countries[0].levels[0], scope_note: 42 }],
        },
      ],
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          levels: [{ ...validCoveragePayload.countries[0].levels[0], scope_note: " " }],
        },
      ],
    },
    {
      ...validCoveragePayload,
      countries: [{ ...validCoveragePayload.countries[0], subjects: [null] }],
    },
    {
      ...validCoveragePayload,
      countries: [{ ...validCoveragePayload.countries[0], coverage_matrix: undefined }],
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          coverage_matrix: [
            { ...validCoveragePayload.countries[0].coverage_matrix[0], status: "unknown" },
          ],
        },
        validCoveragePayload.countries[1],
      ],
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          coverage_matrix: [
            {
              ...validCoveragePayload.countries[0].coverage_matrix[0],
              evidence_scope: "phase_only",
            },
          ],
        },
        validCoveragePayload.countries[1],
      ],
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          coverage_matrix: [
            validCoveragePayload.countries[0].coverage_matrix[0],
            validCoveragePayload.countries[0].coverage_matrix[0],
          ],
        },
        validCoveragePayload.countries[1],
      ],
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          coverage_matrix: [
            {
              ...validCoveragePayload.countries[0].coverage_matrix[0],
              level_name: "Invented level",
            },
          ],
        },
        validCoveragePayload.countries[1],
      ],
    },
    {
      ...validCoveragePayload,
      countries: [{ ...validCoveragePayload.countries[0], subjects: [{}] }],
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          subjects: [{ identifier: "mathematics", name: "Mathematics" }],
        },
        validCoveragePayload.countries[1],
      ],
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          subjects: [
            {
              ...validCoveragePayload.countries[0].subjects[0],
              availability: "missing",
            },
          ],
        },
        validCoveragePayload.countries[1],
      ],
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          availability: "missing",
        },
        validCoveragePayload.countries[1],
      ],
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          subjects: [{ identifier: "mathematics", name: "Mathematics", phase: "primary" }],
        },
        validCoveragePayload.countries[1],
      ],
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          subjects: [
            {
              identifier: "mathematics",
              name: "Mathematics",
              phase: "primary",
              availability: "present_unverified",
            },
          ],
        },
        validCoveragePayload.countries[1],
      ],
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          subjects: [
            {
              ...validCoveragePayload.countries[0].subjects[0],
              identifier: 42,
            },
          ],
        },
        validCoveragePayload.countries[1],
      ],
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          subjects: [
            validCoveragePayload.countries[0].subjects[0],
            validCoveragePayload.countries[0].subjects[0],
          ],
        },
        validCoveragePayload.countries[1],
      ],
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
    {
      ...validCoveragePayload,
      snapshot: { ...validCoveragePayload.snapshot, source_version: null },
    },
    {
      ...validCoveragePayload,
      repository_status: "partial",
      snapshot: { ...validCoveragePayload.snapshot, source_version: null },
    },
    {
      ...validCoveragePayload,
      repository_status: "missing",
      catalog: null,
      source_inventory: null,
      snapshot: { ...validCoveragePayload.snapshot, source_version: null },
    },
    {
      ...validCoveragePayload,
      repository_status: "missing",
      catalog: null,
      source_inventory: null,
      countries: validCoveragePayload.countries.map((country) => ({
        ...country,
        availability: "missing",
        subjects: [],
        coverage_matrix: [],
      })),
    },
    {
      ...validCoveragePayload,
      countries: [
        validCoveragePayload.countries[0],
        {
          ...validCoveragePayload.countries[1],
          code: "GH",
          name: "Ghana",
        },
      ],
    },
    {
      ...validCoveragePayload,
      catalog: {
        ...validCoveragePayload.catalog,
        represented_cells: 2,
        total_cells: 2,
      },
    },
    {
      ...validCoveragePayload,
      catalog: { ...validCoveragePayload.catalog, evidence_cells: 0 },
    },
    {
      ...validCoveragePayload,
      countries: [
        {
          ...validCoveragePayload.countries[0],
          coverage_matrix: [
            {
              ...validCoveragePayload.countries[0].coverage_matrix[0],
              source_url: "https://example.com/",
            },
          ],
        },
        validCoveragePayload.countries[1],
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
