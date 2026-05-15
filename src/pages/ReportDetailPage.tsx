import { useEffect, useState } from "react";
import {
  AlertTriangle as AlertIcon,
  Check as CheckIcon,
  ChevronRight as ChevronIcon,
  Download as DownloadIcon,
  Pencil,
  RefreshCw as RefreshIcon,
} from "lucide-react";
import { Link, Navigate, useParams } from "react-router";

import { OccurrenceMetrics } from "@/components/OccurrenceMetrics";
import { OccurrenceTable } from "@/components/OccurrenceTable";
import ReportListSidebar from "@/components/ReportListSidebar";
import ReprocessModal from "@/components/ReprocessModal";
import { TypeBadge } from "@/components/TypeBadge";
import { useOccurrences } from "@/hooks/useOccurrences";
import { useProcessingStatus } from "@/hooks/useProcessingStatus";
import { useRetryDate } from "@/hooks/useRetryDate";
import { apiClient, type DDRDetail } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function ReportDetailPage() {
  const { id } = useParams();
  const [tab, setTab] = useState<"occurrences" | "failed" | "history">("occurrences");
  const [ddr, setDdr] = useState<DDRDetail | null>(null);
  const [reprocessOpen, setReprocessOpen] = useState(false);
  const [editHistory] = useState([
    { id: "edit-1", field: "Type", original: "Ream", corrected: "Back Ream", date: "2026-04-22", when: "2 min ago" },
    { id: "edit-2", field: "Type", original: "Washout", corrected: "Lost Circulation", date: "2026-04-23", when: "15 min ago" },
  ]);

  if (!id) return <Navigate to="/" replace />;

  const status = useProcessingStatus(id);
  const { data: occurrences, isLoading: occurrencesLoading, refetch: refetchOccurrences } = useOccurrences(id);
  const { retryingDate, handleRetryDate } = useRetryDate(id, status.refresh, status.reconnect);

  useEffect(() => {
    let active = true;
    apiClient.getDDR(id).then((detail) => {
      if (active) setDdr(detail);
    }).catch(() => {});
    return () => { active = false; };
  }, [id]);

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

  const reportName = ddr?.file_path.split("/").at(-1) ?? `DDR ${id}`;
  const uploadedAt = ddr ? new Date(ddr.created_at * 1000).toLocaleDateString() : "—";
  const uploadedBy = ddr?.uploaded_by_username ?? "—";

  const showProcessingSection = status.totalDates > 0 || isProcessing;

  return (
    <>
      <ReportListSidebar selectedId={id} />
      <main className="flex-1 min-w-0 overflow-auto">
        <div className="px-6 py-5 max-w-[1500px] mx-auto animate-fade-in-up">
          {/* Breadcrumb + Title */}
          <div className="flex items-start justify-between gap-4 mb-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-[12px] text-text-muted mb-2">
                <Link to="/" className="hover:text-text-primary transition-colors">Reports</Link>
                <ChevronIcon className="w-3 h-3" />
                <span className="text-text-primary font-medium truncate">{reportName}</span>
              </div>
              <h1 className="text-[20px] font-bold tracking-tight text-text-primary truncate">{ddr?.well_name ?? "—"}</h1>
              <div className="flex items-center gap-3 mt-1 text-[12px] text-text-muted flex-wrap">
                <span>Uploaded {uploadedAt} by {uploadedBy}</span>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {editHistory.length > 0 && (
                <span className="inline-flex items-center gap-1.5 h-8 px-2.5 rounded-md text-[11.5px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                  {editHistory.length} {editHistory.length === 1 ? "correction" : "corrections"} pending
                </span>
              )}
              <button
                type="button"
                onClick={() => setReprocessOpen(true)}
                className="inline-flex items-center gap-1.5 h-9 px-3 rounded-md text-[13px] font-medium bg-white border border-border-default text-text-secondary hover:bg-surface transition-colors"
              >
                <RefreshIcon className="w-3.5 h-3.5" />
                Reprocess
              </button>
              <button className="inline-flex items-center gap-1.5 h-9 px-3 rounded-md text-[13px] font-semibold bg-ces-red text-white hover:bg-ces-red-dark transition-colors">
                <DownloadIcon className="w-3.5 h-3.5" />
                Export .xlsx
              </button>
            </div>
          </div>

          {/* Processing Status */}
          {isProcessing && (
            <div className="rounded-lg border border-border-default bg-white p-4 mb-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[12px] font-semibold text-text-secondary">{processedLabel}</span>
                <span className="text-[12px] font-bold text-ces-red">{Math.round(progressPct)}%</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-surface overflow-hidden">
                <div
                  className="h-full rounded-full bg-ces-red transition-[width] duration-[600ms] ease-out-quart"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
          )}

          {showProcessingSection && !isProcessing && (
            <div className="bg-white border border-border-default rounded-lg px-5 py-4 shadow-[0_1px_2px_rgba(0,0,0,0.04),0_4px_8px_rgba(0,0,0,0.03)] mb-4">
              <div className="flex items-center gap-5">
                <div className="flex-1 min-w-0">
                  <div className="text-[10px] uppercase tracking-wider font-semibold text-ces-red">Extraction</div>
                  <div className="text-[18px] font-bold tracking-tight text-text-primary">Processing status</div>
                  <div className="text-[12px] text-text-muted mt-0.5">
                    <span className="font-semibold text-text-primary">{extractedCount}</span> dates extracted
                    {status.failedCount > 0 && <> · <span className="text-ces-red font-semibold">{status.failedCount} failed</span></>}
                    {status.warningCount > 0 && <> · <span className="text-[#D97706] font-semibold">{status.warningCount} warning</span></>}
                  </div>
                </div>
                <div className="flex items-center gap-6 shrink-0">
                  <ProcStat value={status.successCount} label="Success" tone="success" />
                  {status.warningCount > 0 && <ProcStat value={status.warningCount} label="Warning" tone="warning" />}
                  {status.failedCount > 0 && <ProcStat value={status.failedCount} label="Failed" tone="failed" />}
                </div>
              </div>
            </div>
          )}

          {/* Metrics */}
          <OccurrenceMetrics occurrences={occurrences ?? []} />

          {/* Tabs */}
          <div className="border-b border-border-default flex items-center gap-0 mt-6 mb-4">
            {[
              { k: "occurrences" as const, l: "Occurrences", n: occurrences?.length ?? 0, tone: null as string | null },
              { k: "failed" as const, l: "Failed dates", n: failedDates.length, tone: "warning" as const },
              { k: "history" as const, l: "Edit history", n: editHistory.length, tone: "edit" as const },
            ].map((t) => {
              const active = tab === t.k;
              return (
                <button
                  key={t.k}
                  onClick={() => setTab(t.k)}
                  className={cn(
                    "relative h-10 px-4 flex items-center gap-2 text-[15px] font-semibold transition-colors",
                    active ? "text-ces-red" : "text-text-muted hover:text-text-primary"
                  )}
                >
                  {t.l}
                  {t.n != null && t.n > 0 && (
                    <span
                      className={cn(
                        "px-2 py-0.5 rounded text-[13px] font-bold",
                        active
                          ? "bg-ces-red-light/40 text-ces-red-dark"
                          : t.tone === "warning"
                            ? "bg-ces-red-light/30 text-ces-red"
                            : t.tone === "edit"
                              ? "bg-amber-50 text-amber-700"
                              : "bg-surface text-text-muted"
                      )}
                    >
                      {t.n}
                    </span>
                  )}
                  {active && <span className="absolute -bottom-px left-2 right-2 h-[2px] bg-ces-red rounded-full" />}
                </button>
              );
            })}
          </div>

          {tab === "occurrences" && (
            <section aria-label="Occurrence table">
              <OccurrenceTable
                occurrences={occurrences ?? []}
                isLoading={occurrencesLoading}
              />
            </section>
          )}

          {tab === "failed" && (
            <div className="space-y-3">
              {failedDates.length === 0 ? (
                <div className="flex flex-col items-center justify-center text-center py-16 px-6">
                  <div className="h-12 w-12 rounded-full bg-surface grid place-items-center text-text-muted mb-3">
                    <CheckIcon className="w-5 h-5" />
                  </div>
                  <div className="text-[14px] font-semibold text-text-primary">All dates resolved</div>
                  <div className="text-[13px] text-text-muted mt-1">No failed extractions on this DDR.</div>
                </div>
              ) : (
                failedDates.map((fd) => (
                  <div
                    key={fd.date}
                    className="border border-error-text/20 rounded-lg p-4 bg-error-bg"
                  >
                    <div className="flex items-start gap-3">
                      <div className="h-8 w-8 rounded-md bg-white border border-error-text/20 grid place-items-center text-error-text shrink-0">
                        <AlertIcon className="w-4 h-4" />
                      </div>
                      <div className="flex-1">
                        <div className="font-mono text-[13px] font-semibold text-text-primary">{fd.date}</div>
                        <div className="text-[12.5px] text-text-secondary mt-0.5">{fd.error}</div>
                      </div>
                      <button
                        onClick={() => handleRetryDate(fd.date)}
                        disabled={retryingDate === fd.date}
                        className="inline-flex items-center gap-1.5 h-8 px-3 rounded-md text-[12px] font-medium bg-ces-red text-white hover:bg-ces-red-dark transition-colors disabled:opacity-50 shrink-0"
                      >
                        <RefreshIcon className="w-3 h-3" />
                        {retryingDate === fd.date ? "Retrying…" : "Re-run date"}
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {tab === "history" && (
            <EditHistoryTab rows={editHistory} />
          )}

        </div>
      </main>
      <ReprocessModal
        open={reprocessOpen}
        ddrId={id}
        availableDates={status.rows.map((r) => r.date)}
        onClose={() => setReprocessOpen(false)}
        onSubmitted={(mode) => {
          if (mode !== "occurrences") status.reconnect();
        }}
        onOccurrencesRegenerated={() => {
          void refetchOccurrences();
        }}
      />
    </>
  );
}

function ProcStat({ value, label, tone }: { value: number; label: string; tone: "success" | "warning" | "failed" }) {
  const colors = {
    success: "#047857",
    warning: "#D97706",
    failed: "#C41230",
  };
  return (
    <div className="text-center min-w-[56px]">
      <div className="text-[30px] font-bold leading-none tracking-tight tabular-nums" style={{ color: colors[tone] }}>
        {value}
      </div>
      <div className="text-[9.5px] uppercase tracking-[0.12em] font-semibold mt-1" style={{ color: colors[tone] }}>
        {label}
      </div>
    </div>
  );
}

function EditHistoryTab({ rows }: { rows: Array<{ id: string; field: string; original: string; corrected: string; date: string; when: string }> }) {
  if (rows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-16 px-6">
        <div className="h-12 w-12 rounded-full bg-surface grid place-items-center text-text-muted mb-3">
          <Pencil className="w-5 h-5" aria-hidden="true" />
        </div>
        <div className="text-[14px] font-semibold text-text-primary">No edits yet</div>
        <div className="text-[13px] text-text-muted mt-1">As you correct rows in the occurrence table, edits appear here.</div>
      </div>
    );
  }
  return (
    <div className="border border-border-default rounded-lg overflow-hidden">
      <table className="w-full text-[12.5px]">
        <thead className="bg-surface text-[10.5px] uppercase tracking-wider font-semibold text-text-muted">
          <tr>
            <th className="text-left px-3 py-2 w-16">Field</th>
            <th className="text-left px-3 py-2 w-20">Original</th>
            <th className="text-left px-3 py-2">Corrected</th>
            <th className="text-left px-3 py-2 w-32">Date</th>
            <th className="text-left px-3 py-2 w-28">When</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-border-default hover:bg-slate-50 transition-colors">
              <td className="px-3 py-2 font-medium text-text-primary">{r.field}</td>
              <td className="px-3 py-2 text-text-muted line-through">{r.original}</td>
              <td className="px-3 py-2"><TypeBadge type={r.corrected} /></td>
              <td className="px-3 py-2 font-mono text-[11.5px] text-text-primary">{r.date}</td>
              <td className="px-3 py-2 text-text-muted">{r.when}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
