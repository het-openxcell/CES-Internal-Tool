import { useCallback, useEffect, useState } from "react";

import { ApiError, apiClient, type OccurrenceFilters, type OccurrenceRow } from "@/lib/api";

export function useOccurrences(ddrId: string | undefined) {
  const [data, setData] = useState<OccurrenceRow[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(
    async (signal?: AbortSignal, filters?: OccurrenceFilters) => {
      if (!ddrId) return;
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiClient.getOccurrences(ddrId, filters, signal);
        if (signal?.aborted) return;
        setData(result ?? []);
      } catch (err) {
        if (signal?.aborted) return;
        if (err instanceof ApiError && err.code === "UNAUTHORIZED") return;
        setError("Failed to load occurrences");
      } finally {
        if (!signal?.aborted) setIsLoading(false);
      }
    },
    [ddrId],
  );

  useEffect(() => {
    const controller = new AbortController();
    void loadData(controller.signal);
    return () => controller.abort();
  }, [loadData]);

  return { data, isLoading, error, refetch: () => loadData() };
}

export default useOccurrences;
