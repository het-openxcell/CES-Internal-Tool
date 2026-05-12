import { Navigate, useParams } from "react-router";

import { OccurrenceTable } from "@/components/OccurrenceTable";
import { useOccurrences } from "@/hooks/useOccurrences";
import { useProcessingStatus } from "@/hooks/useProcessingStatus";
import { useRetryDate } from "@/hooks/useRetryDate";
import { cn } from "@/lib/utils";

export default function ReportDetailPage() {
  const { id } = useParams();

  if (!id) return <Navigate to="/" replace />;

  const status = useProcessingStatus(id);
  const { data: occurrences, isLoading: occurrencesLoading } = useOccurrences(id);
  const { retryingDate, handleRetryDate } = useRetryDate(id, status.refresh);

  const processedLabel = `Processing date ${status.currentProcessedCount} of ${status.totalDates || status.currentProcessedCount}…`;
  const extractedCount = status.finalSummary
    ? Math.max(status.finalSummary.total_dates - status.finalSummary.failed_dates, 0)
    : status.successCount + status.warningCount;
  const isProcessing = status.ddrStatus === "processing";
  const progressPct =
    isProcessing && status.totalDates > 0
      ? Math.min(100, (status.currentProcessedCount / status.totalDates) * 100)
      : 0;

  const pillVariant = {
    idle: "border-border-default bg-white text-text-secondary",
    sse: "border-[#FDE68A] bg-[#FFFBEB] text-[#92400E]",
    polling: "border-[#FDE68A] bg-[#FFFBEB] text-[#92400E]",
    closed: "border-[#A7F3D0] bg-[#ECFDF5] text-[#047857]",
    error: "border-[#FECACA] bg-[#FEF2F2] text-error-text",
  }[status.connectionMode];

  const dotColor = {
    idle: "bg-text-muted",
    sse: "bg-[#F59E0B] animate-pulse-dot",
    polling: "bg-[#F59E0B] animate-pulse-dot",
    closed: "bg-[#10B981]",
    error: "bg-ces-red",
  }[status.connectionMode];

  const failedDates = status.rows
    .filter((row) => row.status === "failed" && row.error)
    .map((row) => ({ date: row.date, error: row.error! }));

  return (
    <section className="grid gap-8 animate-fade-in-up">

      {/* ── Processing Status Card ─────────────────────────── */}
      <section
        className="rounded-2xl border border-border-default bg-white"
        aria-label="DDR processing status"
      >
        {/* Top strip: label + title + pill */}
        <div className="flex items-start justify-between gap-4 px-8 pt-7 pb-6 max-[760px]:px-5 max-[760px]:pt-5">
          <div>
            <p className="m-0 mb-1.5 text-ces-red text-[11px] font-bold tracking-[0.08em] uppercase">
              Extraction
            </p>
            <h2 className="m-0 text-[22px] font-bold text-text-primary leading-tight">
              {isProcessing ? processedLabel : "Processing Status"}
            </h2>
            {status.finalSummary ? (
              <p className="mt-1.5 text-sm text-text-muted">
                {extractedCount} dates extracted &bull; {status.finalSummary.failed_dates} failed
              </p>
            ) : null}
          </div>
          <span
            className={cn(
              "inline-flex items-center gap-2 min-h-8 px-3.5 border rounded-full text-xs font-bold capitalize tracking-wide shrink-0",
              pillVariant,
            )}
          >
            <span className={cn("w-[7px] h-[7px] rounded-full shrink-0", dotColor)} />
            {status.connectionMode}
          </span>
        </div>

        {/* Progress bar */}
        {isProcessing && status.totalDates > 0 ? (
          <div className="px-8 pb-5 max-[760px]:px-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-text-muted">
                {status.currentProcessedCount} / {status.totalDates}
              </span>
              <span className="text-xs font-bold text-ces-red">{Math.round(progressPct)}%</span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-[#F3F4F6] overflow-hidden" aria-label="Extraction progress">
              <div
                className="h-full rounded-full bg-ces-red transition-[width] duration-[600ms] ease-out-quart"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        ) : null}

        {/* Divider */}
        <div className="border-t border-border-default" />

        {/* Stat trio */}
        <div className="grid grid-cols-3 divide-x divide-border-default max-[640px]:grid-cols-1 max-[640px]:divide-x-0 max-[640px]:divide-y">
          <div className="px-8 py-7 max-[760px]:px-5">
            <p className="m-0 text-[11px] font-bold uppercase tracking-[0.08em] text-emerald-600 mb-3">
              Success
            </p>
            <span className="block text-[52px] font-black leading-none tabular-nums text-text-primary animate-count-pop">
              {status.successCount}
            </span>
            <p className="m-0 mt-2.5 text-xs text-text-muted">dates extracted</p>
          </div>

          <div className="px-8 py-7 max-[760px]:px-5">
            <p className="m-0 text-[11px] font-bold uppercase tracking-[0.08em] text-amber-500 mb-3">
              Warning
            </p>
            <span className="block text-[52px] font-black leading-none tabular-nums text-text-primary animate-count-pop">
              {status.warningCount}
            </span>
            <p className="m-0 mt-2.5 text-xs text-text-muted">partial extractions</p>
          </div>

          <div className="px-8 py-7 max-[760px]:px-5">
            <p className="m-0 text-[11px] font-bold uppercase tracking-[0.08em] text-ces-red mb-3">
              Failed
            </p>
            <span className="block text-[52px] font-black leading-none tabular-nums text-text-primary animate-count-pop">
              {status.failedCount}
            </span>
            <p className="m-0 mt-2.5 text-xs text-text-muted">dates failed</p>
          </div>
        </div>
      </section>

      {/* ── Occurrence Table ───────────────────────────────── */}
      <section aria-label="Occurrence table">
        <div className="mb-4">
          <p className="m-0 mb-1 text-ces-red text-[11px] font-bold tracking-[0.06em] uppercase">
            Occurrences
          </p>
          <h2 className="m-0 text-xl leading-snug font-semibold">Extracted Occurrences</h2>
        </div>
        <OccurrenceTable
          occurrences={occurrences ?? []}
          failedDates={failedDates}
          isLoading={occurrencesLoading}
          onRetryDate={handleRetryDate}
          retryingDate={retryingDate}
        />
      </section>

    </section>
  );
}
