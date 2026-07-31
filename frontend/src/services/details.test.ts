import { describe, expect, it, vi } from "vitest";

import { getCurriculumDetail } from "./details";

const detail = {
  release_id: "curriculum-test-candidate.1",
  country: "ghana",
  phase: "primary",
  level: "lower_primary",
  subject: "mathematics",
  evidence_scope: "level",
  extraction_status: "extracted",
  extraction_method: "lossless-page-and-native-heading-projection",
  source_files: ["graph.json"],
  curriculum_model: "ghana-standards-based",
  structure_status: "machine_extracted_not_human_verified",
  sections: [
    {
      identifier: "SEC.00000",
      parent_identifier: null,
      kind: "document",
      title: "Mathematics official curriculum",
      source_id: "gh-primary-mathematics",
      source_page: 1,
    },
    {
      identifier: "SEC.00001",
      parent_identifier: "SEC.00000",
      kind: "strand",
      title: "STRAND 1: NUMBER",
      source_id: "gh-primary-mathematics",
      source_page: 42,
    },
  ],
  strands: [{ identifier: "1", name: "Number", sub_strands: ["Counting"] }],
  nodes: [
    {
      code: "B1.1.1.1",
      title: "Count",
      record_kind: "source_page",
      content_standard: "CS1",
      source_id: "gh-primary-mathematics",
      source_page: 42,
      curriculum_path: ["SEC.00000", "SEC.00001"],
      section_identifier: "SEC.00001",
      strand_identifier: "1",
      prerequisite_status: "not_stated_by_authority",
      prerequisites: [],
      evidence_items: [{ kind: "indicator", code: "B1.1.1.1.1", text: "Count objects" }],
      indicators: [
        {
          code: "I1",
          title: "Count objects",
          question_type: "oral",
          difficulty: 1,
          misconception_count: 0,
        },
      ],
    },
  ],
};

describe("getCurriculumDetail", () => {
  it("returns a validated detail payload", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(detail), { status: 200 }));
    await expect(getCurriculumDetail("/detail", undefined, fetcher)).resolves.toEqual(detail);
    expect(fetcher).toHaveBeenCalledWith(
      "/detail",
      expect.objectContaining({ headers: { Accept: "application/json" } }),
    );
  });

  it("accepts a paired null locator and rejects invalid locator boundaries", async () => {
    const withoutLocator = {
      ...detail,
      nodes: [{ ...detail.nodes[0], source_id: null, source_page: null }],
    };
    const valid = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(withoutLocator), { status: 200 }));
    await expect(getCurriculumDetail("/without-locator", undefined, valid)).resolves.toEqual(
      withoutLocator,
    );

    for (const node of [
      { ...detail.nodes[0], source_id: null, source_page: 0 },
      { ...detail.nodes[0], source_id: "", source_page: 1 },
      { ...detail.nodes[0], source_id: "gh-primary-mathematics", source_page: 1.5 },
    ]) {
      const invalid = vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ ...detail, nodes: [node] }), { status: 200 }),
        );
      await expect(getCurriculumDetail("/invalid-locator", undefined, invalid)).rejects.toThrow(
        "invalid payload",
      );
    }
  });

  it("rejects broken native hierarchy references and duplicate identities", async () => {
    const invalidPayloads = [
      {
        ...detail,
        sections: [detail.sections[0], { ...detail.sections[1], parent_identifier: "SEC.unknown" }],
      },
      {
        ...detail,
        nodes: [{ ...detail.nodes[0], curriculum_path: ["SEC.unknown"] }],
      },
      {
        ...detail,
        nodes: [
          {
            ...detail.nodes[0],
            curriculum_path: ["SEC.00000"],
            section_identifier: "SEC.00001",
          },
        ],
      },
      { ...detail, sections: [detail.sections[0], detail.sections[0]] },
      { ...detail, strands: [detail.strands[0], detail.strands[0]] },
      { ...detail, nodes: [detail.nodes[0], detail.nodes[0]] },
      {
        ...detail,
        nodes: [{ ...detail.nodes[0], strand_identifier: "unknown-strand" }],
      },
    ];

    for (const [index, payload] of invalidPayloads.entries()) {
      const invalid = vi
        .fn()
        .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
      await expect(
        getCurriculumDetail(`/invalid-hierarchy-${String(index)}`, undefined, invalid),
      ).rejects.toThrow("invalid payload");
    }
  });

  it("rejects HTTP errors and malformed responses", async () => {
    const failed = vi.fn().mockResolvedValue(new Response("", { status: 404 }));
    await expect(getCurriculumDetail("/missing", undefined, failed)).rejects.toThrow(
      "returned 404",
    );
    const malformed = vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    await expect(getCurriculumDetail("/bad", undefined, malformed)).rejects.toThrow(
      "invalid payload",
    );
    const nonObject = vi.fn().mockResolvedValue(new Response("null", { status: 200 }));
    await expect(getCurriculumDetail("/null", undefined, nonObject)).rejects.toThrow(
      "invalid payload",
    );
    const malformedNode = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ ...detail, nodes: [{ code: 1 }] }), { status: 200 }),
      );
    await expect(getCurriculumDetail("/bad-node", undefined, malformedNode)).rejects.toThrow(
      "invalid payload",
    );
    const incompleteLocator = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          ...detail,
          nodes: [{ ...detail.nodes[0], source_page: null }],
        }),
        { status: 200 },
      ),
    );
    await expect(
      getCurriculumDetail("/bad-source-locator", undefined, incompleteLocator),
    ).rejects.toThrow("invalid payload");
    const malformedStrand = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ...detail, strands: [{ identifier: "1" }] }), {
        status: 200,
      }),
    );
    await expect(getCurriculumDetail("/bad-strand", undefined, malformedStrand)).rejects.toThrow(
      "invalid payload",
    );
    const malformedExtractionMethod = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ ...detail, extraction_method: "" }), { status: 200 }),
      );
    await expect(
      getCurriculumDetail("/bad-extraction-method", undefined, malformedExtractionMethod),
    ).rejects.toThrow("invalid payload");
  });
});
