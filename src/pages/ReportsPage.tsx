import { useCallback, useState } from "react";
import { useNavigate, useParams } from "react-router";

import DDRUploadPanel from "@/components/DDRUploadPanel";
import { EmptyState } from "@/components/ui/empty-state";
import { useProcessingStatus } from "@/hooks/useProcessingStatus";
import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function ReportsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const status = useProcessingStatus(id);
  const [retryingDate, setRetryingDate] = useState<string | null>(null);

  const handleRetryDate = useCallback(
    async (date: string) => {
      if (!id) return;
      setRetryingDate(date);
      try {
        await apiClient.retryDate(id, date);
        await status.refresh();
      } finally {
        setRetryingDate(null);
      }
    },
    [id, status],
  );
  const processedLabel = `Processing date ${status.currentProcessedCount} of ${status.totalDates || status.currentProcessedCount}...`;
  const extractedCount = status.finalSummary
    ? Math.max(status.finalSummary.total_dates - status.finalSummary.failed_dates, 0)
    : status.successCount + status.warningCount;
  const completionMessage = status.finalSummary
    ? `Processing complete - ${extractedCount} dates extracted, ${status.finalSummary.failed_dates} failed`
    : null;

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

  return (
    <section className="grid gap-7 animate-fade-in-up">
      {/* <div className="flex items-center justify-between gap-6 pb-6 border-b border-border-default max-[760px]:flex-col max-[760px]:items-start">
        <div>
          <p className="m-0 mb-1 text-ces-red text-[11px] font-bold tracking-[0.06em] uppercase">Reports</p>
          <h1 className="m-0 text-[28px] leading-tight font-bold text-text-primary tracking-tight">Report {id ?? "selected"}</h1>
        </div>
        <span className={cn("inline-flex items-center gap-2 min-h-8 px-3.5 border rounded-full bg-white text-xs font-bold capitalize tracking-wide", pillVariant)}>
          <span className={cn("w-[7px] h-[7px] rounded-full shrink-0", dotColor)} />
          {status.connectionMode}
        </span>
      </div> */}

      {completionMessage ? (
        <div className="flex items-center gap-3 px-[18px] py-3.5 border border-[#FDE68A] rounded-[10px] text-[#92400E] text-sm font-semibold animate-fade-in-up" style={{ background: "linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%)" }}>
          <svg className="w-5 h-5 shrink-0 text-[#F59E0B]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
          {completionMessage}
        </div>
      ) : null}

      <div className="grid grid-cols-[1fr_minmax(260px,360px)] gap-5 items-start max-[760px]:grid-cols-1">
        <section className="p-6 border border-border-default rounded-xl bg-white" aria-label="DDR processing status">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="m-0 mb-1 text-ces-red text-[11px] font-bold tracking-[0.06em] uppercase">Extraction</p>
              <h2 className="m-0 text-xl leading-snug font-semibold">{status.ddrStatus === "processing" ? processedLabel : "Processing status"}</h2>
            </div>
          </div>

          {status.ddrStatus === "processing" && status.totalDates > 0 ? (
            <div className="relative w-full h-1.5 mt-[18px] rounded-full bg-[#E5E7EB] overflow-hidden" aria-label="Extraction progress">
              <div
                className="h-full rounded-full bg-gradient-to-r from-ces-red to-[#E85D75] transition-[width] duration-[600ms] ease-out-quart"
                style={{ width: `${Math.min(100, (status.currentProcessedCount / status.totalDates) * 100)}%` }}
              />
            </div>
          ) : null}

          <div className="grid grid-cols-3 gap-3 mt-6 max-[760px]:grid-cols-1">
            <div className="relative grid gap-1.5 px-3.5 py-4 border border-border-default rounded-[10px] bg-white overflow-hidden transition-all duration-250 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(0,0,0,0.04)]">
              <span className="block text-text-primary text-[28px] font-extrabold tracking-tight animate-count-pop">{status.successCount}</span>
              <p className="m-0 text-text-muted text-xs font-semibold uppercase tracking-wider">Success</p>
            </div>
            <div className="relative grid gap-1.5 px-3.5 py-4 border border-border-default rounded-[10px] bg-white overflow-hidden transition-all duration-250 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(0,0,0,0.04)]">
              <span className="block text-text-primary text-[28px] font-extrabold tracking-tight animate-count-pop">{status.warningCount}</span>
              <p className="m-0 text-text-muted text-xs font-semibold uppercase tracking-wider">Warning</p>
            </div>
            <div className="relative grid gap-1.5 px-3.5 py-4 border border-border-default rounded-[10px] bg-white overflow-hidden transition-all duration-250 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(0,0,0,0.04)]">
              <span className="block text-text-primary text-[28px] font-extrabold tracking-tight animate-count-pop">{status.failedCount}</span>
              <p className="m-0 text-text-muted text-xs font-semibold uppercase tracking-wider">Failed</p>
            </div>
          </div>

          <div className="grid gap-2 mt-6">
            {status.rows.length === 0 ? (
              <EmptyState
                icon={
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                }
                title="No dates processed yet"
                description="Dates will appear here as the DDR PDF is processed. Upload a new DDR to begin extraction."
              />
            ) : null}
            {status.rows.map((row) => (
              <div className="relative grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 px-[18px] py-3 border border-border-default rounded-[10px] bg-white transition-colors duration-200 hover:bg-[#FAFBFC] hover:border-border-input" key={row.date}>
                <span className="text-sm font-medium text-text-primary tabular-nums tracking-wide">{row.date}</span>
                <div className="flex items-center gap-2">
                  {(row.status === "failed" || row.status === "warning") ? (
                    <button
                      onClick={() => handleRetryDate(row.date)}
                      disabled={retryingDate === row.date}
                      className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-semibold text-[#C41230] border border-[#C41230] rounded bg-white hover:bg-[#FEF2F2] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {retryingDate === row.date ? (
                        <>
                          <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" strokeDasharray="60" strokeDashoffset="20" />
                          </svg>
                          …
                        </>
                      ) : (
                        <>
                          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                            <polyline points="23 4 23 10 17 10" />
                            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                          </svg>
                          Retry
                        </>
                      )}
                    </button>
                  ) : null}
                  <strong className="inline-flex items-center gap-1.5 capitalize text-xs font-bold">{row.status}</strong>
                </div>
                {row.error ? <p className="col-span-full mt-0.5 text-text-muted text-xs leading-relaxed">{row.error}</p> : null}
              </div>
            ))}
          </div>
        </section>

        <DDRUploadPanel onUploaded={(created) => navigate(`/reports/${created.id}`)} />
      </div>
    </section>
  );
}
