import { describe, expect, it, vi } from "vitest";

import { getCurriculumReadiness } from "./readiness";

describe("curriculum readiness client", () => {
  it("accepts the expected ready contract", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ status: "ready", checks: { curriculum_data: "ready" } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(getCurriculumReadiness(fetcher)).resolves.toEqual({ status: "ready" });
    expect(fetcher).toHaveBeenCalledOnce();
    const call = fetcher.mock.calls.at(0);
    expect(call?.[0]).toBe("/api/v1/health/ready");
    expect(call?.[1]?.headers).toEqual({ Accept: "application/json" });
    expect(call?.[1]?.signal).toBeInstanceOf(AbortSignal);
  });

  it("fails closed on an unsuccessful response", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 503 }));

    await expect(getCurriculumReadiness(fetcher)).rejects.toThrow(
      "readiness endpoint returned 503",
    );
  });

  it.each([null, {}, { status: "unknown" }])(
    "fails closed on unexpected response body %#",
    async (payload) => {
      const fetcher = vi
        .fn<typeof fetch>()
        .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));

      await expect(getCurriculumReadiness(fetcher)).rejects.toThrow(
        "readiness endpoint returned an invalid payload",
      );
    },
  );
});
