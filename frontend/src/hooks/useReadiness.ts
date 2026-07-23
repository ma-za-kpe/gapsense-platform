import { useCallback, useEffect, useState } from "react";

import { getCurriculumReadiness } from "../services/readiness";

export type ReadinessState = "checking" | "ready" | "unavailable";

export function useReadiness(): {
  readonly status: ReadinessState;
  readonly retry: () => void;
} {
  const [status, setStatus] = useState<ReadinessState>("checking");

  const completeCheck = useCallback(() => {
    void getCurriculumReadiness().then(
      () => {
        setStatus("ready");
      },
      () => {
        setStatus("unavailable");
      },
    );
  }, []);

  const retry = useCallback(() => {
    setStatus("checking");
    completeCheck();
  }, [completeCheck]);

  useEffect(() => {
    completeCheck();
  }, [completeCheck]);

  return { status, retry };
}
