import { useCallback, useState } from "react";

import { apiClient } from "@/lib/api";

export function useRetryDate(id: string | undefined, refresh: () => Promise<void>) {
  const [retryingDate, setRetryingDate] = useState<string | null>(null);

  const handleRetryDate = useCallback(
    async (date: string) => {
      if (!id) return;
      setRetryingDate(date);
      try {
        await apiClient.retryDate(id, date);
        await refresh();
      } finally {
        setRetryingDate(null);
      }
    },
    [id, refresh],
  );

  return { retryingDate, handleRetryDate };
}
