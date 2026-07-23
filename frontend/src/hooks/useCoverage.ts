import { useCallback, useEffect, useState } from "react";

import { getCurriculumCoverage, type CurriculumCoverageReport } from "../services/coverage";

export type CoverageState =
  | { readonly status: "loading" }
  | { readonly status: "loaded"; readonly report: CurriculumCoverageReport }
  | { readonly status: "unavailable" };

export function useCoverage(): {
  readonly state: CoverageState;
  readonly retry: () => void;
} {
  const [state, setState] = useState<CoverageState>({ status: "loading" });

  const loadCoverage = useCallback(() => {
    void getCurriculumCoverage().then(
      (report) => {
        setState({ status: "loaded", report });
      },
      () => {
        setState({ status: "unavailable" });
      },
    );
  }, []);

  const retry = useCallback(() => {
    setState({ status: "loading" });
    loadCoverage();
  }, [loadCoverage]);

  useEffect(() => {
    loadCoverage();
  }, [loadCoverage]);

  return { state, retry };
}
