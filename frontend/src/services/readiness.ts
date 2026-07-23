const readinessTimeoutMilliseconds = 5_000;

type ReadyPayload = {
  readonly status: "ready";
};

export async function getCurriculumReadiness(fetcher: typeof fetch = fetch): Promise<ReadyPayload> {
  const response = await fetcher("/api/v1/health/ready", {
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(readinessTimeoutMilliseconds),
  });

  if (!response.ok) {
    throw new Error(`readiness endpoint returned ${String(response.status)}`);
  }

  const payload: unknown = await response.json();
  if (
    typeof payload !== "object" ||
    payload === null ||
    !("status" in payload) ||
    payload.status !== "ready"
  ) {
    throw new Error("readiness endpoint returned an invalid payload");
  }

  return { status: "ready" };
}
