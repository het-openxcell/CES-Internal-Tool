import { useMemo, useState } from "react";
import { useParams } from "react-router";

import { EmptyState } from "@/components/ui/empty-state";
import { useProcessingStatus, type ProcessingDateStatus, type ProcessingStatusRow } from "@/hooks/useProcessingStatus";
import { useRetryDate } from "@/hooks/useRetryDate";
import { cn } from "@/lib/utils";

type DateFilter = "all" | "queued" | "processing" | "failed";

const filterLabels: Record<DateFilter, string> = {
  all: "All",
  queued: "Queued",
  processing: "In progress",
  failed: "Failed",
};

const statusTone: Record<ProcessingDateStatus, { label: string; dot: string; pill: string; row: string }> = {
  queued: {
    label: "Queued",
    dot: "bg-[#94A3B8]",
    pill: "border-[#E2E8F0] bg-[#F8FAFC] text-[#475569]",
    row: "border-[#E2E8F0] bg-[#F8FAFC]",
  },
  processing: {
    label: "In progress",
    dot: "bg-[#2563EB] animate-pulse-dot",
    pill: "border-[#BFDBFE] bg-[#EFF6FF] text-[#1D4ED8]",
    row: "border-[#BFDBFE] bg-[#EFF6FF]",
  },
  success: {
    label: "Success",
    dot: "bg-[#10B981]",
    pill: "border-[#A7F3D0] bg-[#ECFDF5] text-[#047857]",
    row: "border-[#D1FAE5] bg-white",
  },
  warning: {
    label: "Warning",
    dot: "bg-[#F59E0B]",
    pill: "border-[#FDE68A] bg-[#FFFBEB] text-[#92400E]",
    row: "border-[#FDE68A] bg-[#FFFBEB]",
  },
  failed: {
    label: "Failed",
    dot: "bg-ces-red",
    pill: "border-[#FECACA] bg-[#FEF2F2] text-error-text",
    row: "border-[#FECACA] bg-[#FEF2F2]",
  },
};

export default function ReportsPage() {
  const { id } = useParams();
  const [filter, setFilter] = useState<DateFilter>("all");
  const status = useProcessingStatus(id);
  const { retryingDate, handleRetryDate } = useRetryDate(id, status.refresh);
  const processedLabel = `Processing date ${status.currentProcessedCount} of ${status.totalDates || status.currentProcessedCount}`;
  const extractedCount = status.finalSummary
    ? Math.max(status.finalSummary.total_dates - status.finalSummary.failed_dates, 0)
    : status.successCount + status.warningCount;
  const completionMessage = status.finalSummary
    ? `Processing complete: ${extractedCount} dates extracted, ${status.finalSummary.failed_dates} failed`
    : null;

  const filteredRows = useMemo(() => {
    if (filter === "all") {
      return status.rows;
    }
    return status.rows.filter((row) => row.status === filter);
  }, [filter, status.rows]);

  const activeConnection = status.connectionMode === "sse" || status.connectionMode === "polling";
  const progressPercent = status.totalDates > 0 ? Math.min(100, (status.currentProcessedCount / status.totalDates) * 100) : 0;
  const filterCounts: Record<DateFilter, number> = {
    all: status.rows.length,
    queued: status.queuedCount,
    processing: status.processingCount,
    failed: status.failedCount,
  };

  return (
    <section className="grid gap-5 animate-fade-in-up">
      <div className="rounded-2xl border border-border-default bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)] overflow-hidden">
        <div className="px-5 py-4 border-b border-border-default bg-[#FBFCFD] flex items-start justify-between gap-4 max-[760px]:flex-col">
          <div>
            <p className="m-0 mb-1 text-ces-red text-[11px] font-bold tracking-[0.08em] uppercase">DDR extraction</p>
            <h1 className="m-0 text-[22px] leading-tight font-bold text-text-primary tracking-tight">
              {status.ddrStatus === "processing" ? processedLabel : `Report ${id ?? "selected"}`}
            </h1>
            <p className="m-0 mt-1 text-[13px] text-text-muted">
              Queued dates stay visible. Live stream opens only while work remains.
            </p>
          </div>
          <ConnectionPill mode={status.connectionMode} active={activeConnection} />
        </div>

        {completionMessage ? (
          <div className="mx-5 mt-4 flex items-center gap-3 px-4 py-3 border border-[#A7F3D0] rounded-xl bg-[#ECFDF5] text-[#047857] text-sm font-semibold">
            <CheckIcon className="w-5 h-5 shrink-0" />
            {completionMessage}
          </div>
        ) : null}

        {status.error ? (
          <div className="mx-5 mt-4 flex items-center gap-3 px-4 py-3 border border-[#FECACA] rounded-xl bg-[#FEF2F2] text-error-text text-sm font-semibold">
            <AlertIcon className="w-5 h-5 shrink-0" />
            {status.error}
          </div>
        ) : null}

        <div className="p-5 grid gap-5">
          <div className="grid grid-cols-5 gap-3 max-[980px]:grid-cols-2 max-[560px]:grid-cols-1">
            <StatusMetric label="Total dates" value={status.totalDates} tone="neutral" />
            <StatusMetric label="In progress" value={status.processingCount} tone="processing" />
            <StatusMetric label="Queued" value={status.queuedCount} tone="queued" />
            <StatusMetric label="Success" value={status.successCount + status.warningCount} tone="success" />
            <StatusMetric label="Failed" value={status.failedCount} tone="failed" />
          </div>

          {status.ddrStatus === "processing" && status.totalDates > 0 ? (
            <div className="grid gap-2" aria-label="Extraction progress">
              <div className="flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                <span>{status.currentProcessedCount} processed</span>
                <span>{Math.round(progressPercent)}%</span>
              </div>
              <div className="relative h-2 w-full overflow-hidden rounded-full bg-[#E5E7EB]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-ces-red to-[#E85D75] transition-[width] duration-[600ms] ease-out-quart"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
          ) : null}

          <div className="flex items-center justify-between gap-3 max-[760px]:flex-col max-[760px]:items-stretch">
            <div className="flex flex-wrap gap-2" aria-label="Date status filters">
              {(Object.keys(filterLabels) as DateFilter[]).map((key) => (
                <button
                  type="button"
                  key={key}
                  onClick={() => setFilter(key)}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-bold transition-colors",
                    filter === key
                      ? "border-ces-red bg-[#FEF2F2] text-ces-red"
                      : "border-border-default bg-white text-text-secondary hover:border-border-input hover:bg-surface",
                  )}
                >
                  <span>{filterLabels[key]}</span>
                  <span className="rounded-full bg-white/80 px-1.5 py-0.5 text-[10px] tabular-nums">{filterCounts[key]}</span>
                </button>
              ))}
            </div>
            <p className="m-0 text-xs text-text-muted">
              {activeConnection ? "Live connection active" : "No live connection needed"}
            </p>
          </div>

          <DateRows rows={filteredRows} retryingDate={retryingDate} onRetry={handleRetryDate} />
        </div>
      </div>
    </section>
  );
}

function StatusMetric({ label, value, tone }: { label: string; value: number; tone: "neutral" | "processing" | "queued" | "success" | "failed" }) {
  const color = {
    neutral: "text-text-primary",
    processing: "text-[#1D4ED8]",
    queued: "text-[#475569]",
    success: "text-[#047857]",
    failed: "text-ces-red",
  }[tone];

  return (
    <div className="rounded-xl border border-border-default bg-white px-4 py-3 shadow-[0_1px_2px_rgba(15,23,42,0.03)]">
      <div className={cn("text-[26px] leading-none font-extrabold tracking-tight tabular-nums", color)}>{value}</div>
      <div className="mt-1.5 text-[11px] text-text-muted uppercase tracking-wider font-semibold">{label}</div>
    </div>
  );
}

function DateRows({ rows, retryingDate, onRetry }: { rows: ProcessingStatusRow[]; retryingDate: string | null; onRetry: (date: string) => void }) {
  if (rows.length === 0) {
    return (
      <EmptyState
        icon={<ClockIcon className="w-6 h-6" />}
        title="No dates in this view"
        description="Switch filters to inspect queued, failed, in-progress, and completed extraction dates."
      />
    );
  }

  return (
    <div className="grid gap-2" aria-label="DDR date statuses">
      {rows.map((row) => (
        <DateRow key={row.date} row={row} retrying={retryingDate === row.date} onRetry={onRetry} />
      ))}
    </div>
  );
}

function DateRow({ row, retrying, onRetry }: { row: ProcessingStatusRow; retrying: boolean; onRetry: (date: string) => void }) {
  const tone = statusTone[row.status];
  const canRetry = row.status === "failed" || row.status === "warning";

  return (
    <div className={cn("grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 rounded-xl border px-4 py-3 transition-colors", tone.row)}>
      <div className="min-w-0 flex items-center gap-3">
        <span className={cn("h-2.5 w-2.5 rounded-full shrink-0", tone.dot)} />
        <div className="min-w-0">
          <div className="text-sm font-bold text-text-primary tabular-nums tracking-wide">{formatDate(row.date)}</div>
          {row.error ? <p className="m-0 mt-1 text-text-muted text-xs leading-relaxed">{row.error}</p> : null}
        </div>
      </div>
      <div className="flex items-center gap-2">
        {canRetry ? (
          <button
            onClick={() => onRetry(row.date)}
            disabled={retrying}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-bold text-ces-red border border-ces-red rounded-md bg-white hover:bg-[#FEF2F2] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {retrying ? <SpinnerIcon className="w-3.5 h-3.5 animate-spin" /> : <RetryIcon className="w-3.5 h-3.5" />}
            {retrying ? "Retrying" : "Retry"}
          </button>
        ) : null}
        <strong className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-bold", tone.pill)}>
          {tone.label}
        </strong>
      </div>
    </div>
  );
}

function ConnectionPill({ mode, active }: { mode: string; active: boolean }) {
  const styles = active
    ? "border-[#BFDBFE] bg-[#EFF6FF] text-[#1D4ED8]"
    : mode === "error"
      ? "border-[#FECACA] bg-[#FEF2F2] text-error-text"
      : "border-border-default bg-white text-text-secondary";

  return (
    <span className={cn("inline-flex items-center gap-2 min-h-8 px-3.5 border rounded-full text-xs font-bold capitalize", styles)}>
      <span className={cn("w-[7px] h-[7px] rounded-full shrink-0", active ? "bg-[#2563EB] animate-pulse-dot" : "bg-text-muted")} />
      {active ? "live" : mode}
    </span>
  );
}

function formatDate(date: string) {
  if (/^\d{8}$/.test(date)) {
    return `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6)}`;
  }
  return date;
}

function CheckIcon({ className }: { className?: string }) {
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>;
}

function AlertIcon({ className }: { className?: string }) {
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>;
}

function ClockIcon({ className }: { className?: string }) {
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>;
}

function RetryIcon({ className }: { className?: string }) {
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" /></svg>;
}

function SpinnerIcon({ className }: { className?: string }) {
  return <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" strokeDasharray="60" strokeDashoffset="20" /></svg>;
}
