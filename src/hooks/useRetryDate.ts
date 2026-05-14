import { useCallback, useState } from "react";

import { apiClient } from "@/lib/api";

export function useRetryDate(id: string | undefined, refresh: () => Promise<void>, reconnect?: () => void) {
  const [retryingDate, setRetryingDate] = useState<string | null>(null);

  const handleRetryDate = useCallback(
    async (date: string) => {
      if (!id) return;
      setRetryingDate(date);
      try {
        await apiClient.retryDate(id, date);
        // reconnect reopens SSE so live date_started/complete events arrive;
        // fallback to refresh if reconnect not provided
        if (reconnect) {
          reconnect();
        } else {
          await refresh();
        }
      } finally {
        setRetryingDate(null);
      }
    },
    [id, refresh, reconnect],
  );

  return { retryingDate, handleRetryDate };
}
