import { describe, expect, it, vi } from "vitest";

import { getCurriculumDetail } from "./details";

const detail = {
  country: "ghana",
  phase: "primary",
  level: "lower_primary",
  subject: "mathematics",
  evidence_scope: "phase_only",
  extraction_status: "extracted",
  source_files: ["graph.json"],
  strands: [],
  nodes: [],
};

describe("getCurriculumDetail", () => {
  it("returns a validated detail payload", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(detail), { status: 200 }));
    await expect(getCurriculumDetail("/detail", fetcher)).resolves.toEqual(detail);
    expect(fetcher).toHaveBeenCalledWith(
      "/detail",
      expect.objectContaining({ headers: { Accept: "application/json" } }),
    );
  });

  it("rejects HTTP errors and malformed responses", async () => {
    const failed = vi.fn().mockResolvedValue(new Response("", { status: 404 }));
    await expect(getCurriculumDetail("/missing", failed)).rejects.toThrow("returned 404");
    const malformed = vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    await expect(getCurriculumDetail("/bad", malformed)).rejects.toThrow("invalid payload");
    const nonObject = vi.fn().mockResolvedValue(new Response("null", { status: 200 }));
    await expect(getCurriculumDetail("/null", nonObject)).rejects.toThrow("invalid payload");
  });
});
