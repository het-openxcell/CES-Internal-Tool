import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { apiClient, type DDRDateStatus, type DDRDetail, type DDRStatus } from "@/lib/api";

export type ProcessingDateStatus = DDRDateStatus | "processing";

export type ProcessingStatusRow = {
  date: string;
  status: ProcessingDateStatus;
  error?: string;
  rawResponseId?: string;
};

export type ProcessingCompleteSummary = {
  total_dates: number;
  failed_dates: number;
  warning_dates: number;
  total_occurrences: number;
};

export type ProcessingConnectionMode = "idle" | "sse" | "polling" | "closed" | "error";

type DateStartedPayload = {
  date: string;
};

type DateCompletePayload = {
  date: string;
  status: "success" | "warning";
  occurrences_count: number;
};

type DateFailedPayload = {
  date: string;
  error: string;
  raw_response_id: string;
};

function rowsFromDetail(detail: DDRDetail) {
  const rows = (detail.dates ?? [])
    .map((row) => ({
      date: row.date,
      status: row.status as ProcessingDateStatus,
      error: errorFromLog(row.error_log),
      rawResponseId: rawResponseId(row),
    }))
    .sort((left, right) => left.date.localeCompare(right.date));

  if (detail.status !== "processing") {
    return rows;
  }

  let promoted = false;
  return rows.map((row) => {
    if (promoted || row.status !== "queued") {
      return row;
    }
    promoted = true;
    return { ...row, status: "processing" as ProcessingDateStatus };
  });
}

function needsLiveConnection(detail: DDRDetail) {
  return detail.status === "processing" || (detail.dates ?? []).some((row) => row.status === "queued");
}

function errorFromLog(errorLog: Record<string, unknown> | null | undefined) {
  if (!errorLog) {
    return undefined;
  }
  for (const key of ["detail", "reason", "error", "code"]) {
    const value = errorLog[key];
    if (value) {
      return String(value);
    }
  }
  const errors = errorLog.errors;
  return errors ? String(errors) : undefined;
}

function rawResponseId(row: NonNullable<DDRDetail["dates"]>[number]) {
  const rawResponse = row.raw_response;
  if (rawResponse) {
    for (const key of ["id", "raw_response_id", "response_id"]) {
      const value = rawResponse[key];
      if (value) {
        return String(value);
      }
    }
  }
  return row.id;
}

function upsertRow(rows: ProcessingStatusRow[], next: ProcessingStatusRow) {
  const index = rows.findIndex((row) => row.date === next.date);
  if (index === -1) {
    return [...rows, next].sort((left, right) => left.date.localeCompare(right.date));
  }
  return rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...next } : row));
}

function summaryFromRows(detail: DDRDetail, currentRows: ProcessingStatusRow[], totalDates: number) {
  const failedDates = currentRows.filter((row) => row.status === "failed").length;
  const warningDates = currentRows.filter((row) => row.status === "warning").length;
  return {
    total_dates: detail.dates?.length ?? (totalDates || currentRows.length),
    failed_dates: failedDates,
    warning_dates: warningDates,
    total_occurrences: 0,
  };
}

export function useProcessingStatus(ddrId?: string) {
  const [connectionMode, setConnectionMode] = useState<ProcessingConnectionMode>("idle");
  const [ddrStatus, setDdrStatus] = useState<DDRStatus>("queued");
  const [rows, setRows] = useState<ProcessingStatusRow[]>([]);
  const [totalDates, setTotalDates] = useState(0);
  const [finalSummary, setFinalSummary] = useState<ProcessingCompleteSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const completedRef = useRef(false);
  const rowsRef = useRef<ProcessingStatusRow[]>([]);
  const totalDatesRef = useRef(0);

  useEffect(() => {
    rowsRef.current = rows;
    totalDatesRef.current = totalDates;
  }, [rows, totalDates]);

  const applyDetail = useCallback((detail: DDRDetail) => {
    const detailRows = rowsFromDetail(detail);
    setDdrStatus(detail.status);
    setRows(detailRows);
    setTotalDates(detail.dates?.length ?? detailRows.length);
    return detailRows;
  }, []);

  useEffect(() => {
    if (!ddrId) {
      setConnectionMode("idle");
      setRows([]);
      setTotalDates(0);
      setFinalSummary(null);
      setError(null);
      rowsRef.current = [];
      totalDatesRef.current = 0;
      return;
    }

    let active = true;
    let source: EventSource | null = null;
    let pollInterval: ReturnType<typeof setInterval> | null = null;
    setConnectionMode("idle");
    setRows([]);
    setTotalDates(0);
    setFinalSummary(null);
    setError(null);
    completedRef.current = false;
    rowsRef.current = [];
    totalDatesRef.current = 0;

    const stopPolling = () => {
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
    };

    const poll = async () => {
      try {
        const detail = await apiClient.getDDR(ddrId);
        if (!active) {
          return;
        }
        const detailRows = applyDetail(detail);
        if (detail.status === "complete" || detail.status === "failed") {
          completedRef.current = true;
          setConnectionMode("closed");
          setFinalSummary(summaryFromRows(detail, detailRows, totalDatesRef.current));
          stopPolling();
        }
      } catch {
        if (active) {
          setError("Status polling failed");
          setConnectionMode("error");
        }
      }
    };

    const startPolling = () => {
      if (pollInterval) {
        return;
      }
      setConnectionMode("polling");
      pollInterval = setInterval(poll, 3000);
    };

    const handleDateStarted = (event: MessageEvent<string>) => {
      const payload = JSON.parse(event.data) as DateStartedPayload;
      setRows((current) => upsertRow(current, { date: payload.date, status: "processing" }));
      setDdrStatus("processing");
    };

    const handleDateComplete = (event: MessageEvent<string>) => {
      const payload = JSON.parse(event.data) as DateCompletePayload;
      setRows((current) => upsertRow(current, { date: payload.date, status: payload.status }));
      setDdrStatus("processing");
    };

    const handleDateFailed = (event: MessageEvent<string>) => {
      const payload = JSON.parse(event.data) as DateFailedPayload;
      setRows((current) =>
        upsertRow(current, {
          date: payload.date,
          status: "failed",
          error: payload.error,
          rawResponseId: payload.raw_response_id,
        }),
      );
      setDdrStatus("processing");
    };

    const handleProcessingComplete = (event: MessageEvent<string>) => {
      const payload = JSON.parse(event.data) as ProcessingCompleteSummary;
      completedRef.current = true;
      setFinalSummary(payload);
      setTotalDates(payload.total_dates);
      setDdrStatus(payload.failed_dates === payload.total_dates ? "failed" : "complete");
      setConnectionMode("closed");
      source?.close();
      stopPolling();
    };

    const openStream = () => {
      source = new EventSource(apiClient.ddrStatusStreamUrl(ddrId));
      setConnectionMode("sse");
      source.addEventListener("date_started", handleDateStarted);
      source.addEventListener("date_complete", handleDateComplete);
      source.addEventListener("date_failed", handleDateFailed);
      source.addEventListener("processing_complete", handleProcessingComplete);
      source.onerror = () => {
        if (!completedRef.current) {
          source?.close();
          startPolling();
        }
      };
    };

    void (async () => {
      try {
        const detail = await apiClient.getDDR(ddrId);
        if (!active) {
          return;
        }
        const detailRows = applyDetail(detail);
        if (detail.status === "complete" || detail.status === "failed") {
          completedRef.current = true;
          setConnectionMode("closed");
          setFinalSummary(summaryFromRows(detail, detailRows, detail.dates?.length ?? detailRows.length));
          return;
        }
        if (needsLiveConnection(detail)) {
          openStream();
          return;
        }
        setConnectionMode("closed");
      } catch {
        if (active) {
          setError("Status load failed");
          setConnectionMode("error");
        }
      }
    })();

    return () => {
      active = false;
      source?.removeEventListener("date_started", handleDateStarted);
      source?.removeEventListener("date_complete", handleDateComplete);
      source?.removeEventListener("date_failed", handleDateFailed);
      source?.removeEventListener("processing_complete", handleProcessingComplete);
      source?.close();
      stopPolling();
    };
  }, [applyDetail, ddrId]);

  const counts = useMemo(() => {
    const queuedCount = rows.filter((row) => row.status === "queued").length;
    const processingCount = rows.filter((row) => row.status === "processing").length;
    const successCount = rows.filter((row) => row.status === "success").length;
    const warningCount = rows.filter((row) => row.status === "warning").length;
    const failedCount = rows.filter((row) => row.status === "failed").length;
    return {
      queuedCount,
      processingCount,
      successCount,
      warningCount,
      failedCount,
      currentProcessedCount: successCount + warningCount + failedCount,
    };
  }, [rows]);

  const refresh = async () => {
    if (!ddrId) return;
    try {
      const detail = await apiClient.getDDR(ddrId);
      const detailRows = applyDetail(detail);
      if (detail.status === "complete" || detail.status === "failed") {
        completedRef.current = true;
        setConnectionMode("closed");
        const failedDates = detailRows.filter((row) => row.status === "failed").length;
        const warningDates = detailRows.filter((row) => row.status === "warning").length;
        const occurrences = await apiClient.getOccurrences(ddrId);
        setFinalSummary({
          total_dates: detail.dates?.length ?? detailRows.length,
          failed_dates: failedDates,
          warning_dates: warningDates,
          total_occurrences: occurrences?.length ?? 0,
        });
      } else {
        completedRef.current = false;
        setFinalSummary(null);
      }
    } catch {
      setError("Refresh failed");
    }
  };

  return {
    connectionMode,
    ddrStatus,
    rows,
    ...counts,
    totalDates: totalDates || rows.length,
    finalSummary,
    error,
    refresh,
  };
}
