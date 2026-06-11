import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import { useProcessingStatus } from "@/hooks/useProcessingStatus";
import { fireNotification, requestNotificationPermission } from "@/lib/notifications";

type TrackerValue = { track: (ddrId: string) => void };

const ProcessingTrackerContext = createContext<TrackerValue | null>(null);

function DdrStatusWatcher({ ddrId, onComplete }: { ddrId: string; onComplete: (ddrId: string) => void }) {
  const { ddrStatus, finalSummary, connectionMode } = useProcessingStatus(ddrId);
  const firedRef = useRef(false);
  const wasLiveRef = useRef(false);

  useEffect(() => {
    if (connectionMode === "sse" || connectionMode === "polling") {
      wasLiveRef.current = true;
    }
  }, [connectionMode]);

  useEffect(() => {
    if (firedRef.current || !finalSummary) {
      return;
    }
    if (ddrStatus !== "complete" && ddrStatus !== "failed" && ddrStatus !== "cancelled") {
      return;
    }
    firedRef.current = true;
    // Only notify if we actually watched a live run finish — never on opening an already-finished DDR.
    if (wasLiveRef.current) {
      const allFailed = finalSummary.failed_dates === finalSummary.total_dates;
      const title =
        ddrStatus === "cancelled"
          ? "DDR Processing Cancelled"
          : allFailed
            ? "DDR Processing Failed"
            : "DDR Processing Complete";
      const body = `${finalSummary.total_dates} dates — ${finalSummary.failed_dates} failed, ${finalSummary.warning_dates} warnings`;
      fireNotification(title, body);
    }
    onComplete(ddrId);
  }, [ddrStatus, finalSummary, ddrId, onComplete]);

  return null;
}

export function ProcessingTrackerProvider({ children }: { children: ReactNode }) {
  const [ids, setIds] = useState<string[]>([]);

  useEffect(() => {
    void requestNotificationPermission();
  }, []);

  const track = useCallback((ddrId: string) => {
    setIds((current) => (current.includes(ddrId) ? current : [...current, ddrId]));
  }, []);

  const untrack = useCallback((ddrId: string) => {
    setIds((current) => current.filter((id) => id !== ddrId));
  }, []);

  return (
    <ProcessingTrackerContext.Provider value={{ track }}>
      {ids.map((ddrId) => (
        <DdrStatusWatcher key={ddrId} ddrId={ddrId} onComplete={untrack} />
      ))}
      {children}
    </ProcessingTrackerContext.Provider>
  );
}

export function useProcessingTracker() {
  const ctx = useContext(ProcessingTrackerContext);
  return ctx ?? { track: () => {} };
}
