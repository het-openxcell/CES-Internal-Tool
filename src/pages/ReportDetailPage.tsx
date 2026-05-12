import { Navigate, useParams } from "react-router";

import { OccurrenceMetrics } from "@/components/OccurrenceMetrics";
import { OccurrenceTable } from "@/components/OccurrenceTable";
import { useOccurrences } from "@/hooks/useOccurrences";
import { useProcessingStatus } from "@/hooks/useProcessingStatus";
import { useRetryDate } from "@/hooks/useRetryDate";

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
        {/* Header: label + title + creative stat row */}
        <div className="px-8 pt-7 pb-5 max-[760px]:px-5 max-[760px]:pt-5">
          <p className="m-0 mb-1.5 text-ces-red text-[11px] font-bold tracking-[0.08em] uppercase">
            Extraction
          </p>
          <div className="flex items-baseline justify-between gap-4 max-[640px]:flex-col">
            <div>
              <h2 className="m-0 text-[22px] font-bold text-text-primary leading-tight">
                {isProcessing ? processedLabel : "Processing Status"}
              </h2>
              {status.finalSummary ? (
                <p className="mt-1 text-sm text-text-muted">
                  {extractedCount} dates extracted &bull; {status.finalSummary.failed_dates} failed
                </p>
              ) : null}
            </div>
            <div className="flex items-center gap-1 shrink-0 rounded-2xl bg-[#F3F4F6] p-1 max-[640px]:self-stretch max-[640px]:justify-around">
              <div className="flex flex-col items-center px-4 py-1.5 rounded-xl min-w-[64px]">
                <span className="text-[26px] font-black leading-none tabular-nums text-emerald-600">{status.successCount}</span>
                <span className="mt-0.5 text-[10px] font-bold uppercase tracking-widest text-emerald-500">Success</span>
              </div>
              <div className="flex flex-col items-center px-4 py-1.5 rounded-xl min-w-[64px]">
                <span className="text-[26px] font-black leading-none tabular-nums text-amber-600">{status.warningCount}</span>
                <span className="mt-0.5 text-[10px] font-bold uppercase tracking-widest text-amber-500">Warning</span>
              </div>
              <div className="flex flex-col items-center px-4 py-1.5 rounded-xl min-w-[64px]">
                <span className="text-[26px] font-black leading-none tabular-nums text-red-600">{status.failedCount}</span>
                <span className="mt-0.5 text-[10px] font-bold uppercase tracking-widest text-red-500">Failed</span>
              </div>
            </div>
          </div>
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
      </section>

      {/* ── Occurrence Metrics ─────────────────────────────── */}
      <OccurrenceMetrics occurrences={occurrences ?? []} />

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
