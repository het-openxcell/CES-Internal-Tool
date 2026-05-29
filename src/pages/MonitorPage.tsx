import { useCallback, useEffect, useState } from "react";
import { RefreshCw as RefreshCwIcon } from "lucide-react";
import { Link } from "react-router";

import { TypeBadge } from "@/components/TypeBadge";
import { SectionBadge } from "@/components/SectionBadge";
import { apiClient, type Correction, type MonitorMetrics, type QueueItem } from "@/lib/api";
import { cn } from "@/lib/utils";

// ─── helpers ─────────────────────────────────────────────────────────────────

function fmtMoney(n: number) {
  return `$${n.toFixed(2)}`;
}

function fmtTs(ts: number) {
  const d = new Date(ts * 1000);
  const today = new Date();
  if (d.toDateString() === today.toDateString()) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) {
    return `Yesterday ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  }
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

// ─── BigMetric card ───────────────────────────────────────────────────────────

type MetricTone = "neutral" | "edit" | "success" | "failed";

function BigMetric({
  label,
  value,
  sub,
  delta,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  sub?: string;
  delta?: string;
  tone?: MetricTone;
}) {
  const toneClass: Record<MetricTone, string> = {
    neutral: "text-gray-900",
    edit: "text-amber-600",
    success: "text-emerald-700",
    failed: "text-red-600",
  };
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 shadow-sm">
      <div className="text-[12px] uppercase tracking-wider font-semibold text-gray-500">{label}</div>
      <div className="flex items-baseline gap-2 mt-1">
        <div className={cn("text-[30px] font-bold tracking-tight leading-none", toneClass[tone])}>{value}</div>
        {sub && <div className="text-[13px] text-gray-500">{sub}</div>}
      </div>
      {delta && (
        <div className="text-[12.5px] text-gray-500 mt-1.5">{delta}</div>
      )}
    </div>
  );
}

// ─── display status derived from queue item ───────────────────────────────────

type DisplayStatus = "processing" | "queued" | "complete" | "warning" | "failed";

function getDisplayStatus(item: QueueItem): { kind: DisplayStatus; label: string } {
  if (item.status === "processing") return { kind: "processing", label: "Processing" };
  if (item.status === "queued") return { kind: "queued", label: "Queued" };
  if (item.status === "failed") return { kind: "failed", label: "Failed" };
  // complete — check date outcomes
  if (item.date_failed > 0) return { kind: "failed", label: "Failed dates" };
  if (item.date_warning > 0) return { kind: "warning", label: `${item.date_warning} warning` };
  return { kind: "complete", label: "Complete" };
}

// ─── StatusDot ────────────────────────────────────────────────────────────────

function StatusDot({ kind, pulse }: { kind: DisplayStatus; pulse?: boolean }) {
  const color =
    kind === "processing" ? "bg-blue-500"
    : kind === "queued" ? "bg-gray-400"
    : kind === "complete" ? "bg-emerald-500"
    : kind === "warning" ? "bg-amber-500"
    : "bg-red-500";
  return (
    <span className="relative flex h-2.5 w-2.5">
      {pulse && <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", color)} />}
      <span className={cn("relative inline-flex rounded-full h-2.5 w-2.5", color)} />
    </span>
  );
}

function StatusPill({ kind, label }: { kind: DisplayStatus; label: string }) {
  const dotColor =
    kind === "processing" ? "bg-blue-500"
    : kind === "queued" ? "bg-gray-400"
    : kind === "complete" ? "bg-emerald-500"
    : kind === "warning" ? "bg-amber-500"
    : "bg-red-500";
  const pillCls =
    kind === "processing" ? "bg-blue-50 text-blue-800 border-blue-200"
    : kind === "queued" ? "bg-gray-50 text-gray-700 border-gray-200"
    : kind === "complete" ? "bg-emerald-50 text-emerald-800 border-emerald-200"
    : kind === "warning" ? "bg-amber-50 text-amber-800 border-amber-200"
    : "bg-red-50 text-red-800 border-red-200";
  return (
    <span className={cn("inline-flex items-center gap-1.5 px-3 py-1 rounded border text-[13px] font-semibold", pillCls)}>
      <span className={cn("inline-block w-1.5 h-1.5 rounded-full shrink-0", dotColor)} />
      {label}
    </span>
  );
}

// ─── PipelineQueue ────────────────────────────────────────────────────────────

function PipelineQueue({ items, loading }: { items: QueueItem[]; loading: boolean }) {
  if (loading) return <LoadingTable cols={7} />;

  const displayName = (item: QueueItem) => {
    const base = item.well_name ?? item.file_path.split("/").pop() ?? item.id;
    return base.length > 55 ? base.slice(0, 55) + "…" : base;
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      <table className="w-full text-[15px]">
        <thead className="bg-gray-50 text-[13px] uppercase tracking-wider font-bold text-gray-500">
          <tr>
            <th className="text-left px-4 py-2.5 w-8" />
            <th className="text-left px-4 py-2.5">Report</th>
            <th className="text-left px-4 py-2.5 w-40">Operator</th>
            <th className="text-left px-4 py-2.5 w-36">Status</th>
            <th className="text-left px-4 py-2.5 w-64">Progress</th>
            <th className="text-left px-4 py-2.5 w-36">Started</th>
            <th className="text-right px-4 py-2.5 w-24" />
          </tr>
        </thead>
        <tbody>
          {items.length === 0 && (
            <tr>
              <td colSpan={7} className="px-4 py-8 text-center text-gray-400 text-[14px]">
                No DDRs in queue
              </td>
            </tr>
          )}
          {items.map((q) => {
            const dateProgress = q.date_success + q.date_warning + q.date_failed;
            const pct = q.date_total > 0 ? Math.round((dateProgress / q.date_total) * 100) : 0;
            const ds = getDisplayStatus(q);
            return (
              <tr key={q.id} className="border-t border-gray-100 hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3">
                  <StatusDot kind={ds.kind} pulse={ds.kind === "processing"} />
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900 truncate max-w-[300px]">{displayName(q)}</div>
                  <div className="text-[12.5px] text-gray-400 font-mono mt-0.5">{q.id.slice(0, 12)}…</div>
                </td>
                <td className="px-4 py-3 text-gray-700">{q.operator ?? q.area ?? "—"}</td>
                <td className="px-4 py-3">
                  <StatusPill kind={ds.kind} label={ds.label} />
                </td>
                <td className="px-4 py-3">
                  {q.status === "processing" ? (
                    <div>
                      <div className="text-[13px] text-gray-500 mb-1.5">
                        Date {dateProgress} of {q.date_total}
                      </div>
                      <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden w-44">
                        <div className="h-full bg-blue-500 transition-all" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  ) : q.status === "queued" ? (
                    <span className="text-[14px] text-gray-500">—</span>
                  ) : (
                    <div className="flex items-center gap-1.5 text-[14px] text-gray-700">
                      <span>
                        <span className="font-semibold">{dateProgress}</span>/{q.date_total} dates
                      </span>
                      {q.date_failed > 0 && (
                        <span className="text-red-600 font-medium">· {q.date_failed} failed</span>
                      )}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-500 text-[13.5px]">{fmtTs(q.created_at)}</td>
                <td className="px-4 py-3 text-right">
                  {q.status === "queued" && (
                    <button className="text-gray-400 hover:text-gray-700 text-[13.5px]">Cancel</button>
                  )}
                  {(q.status === "complete" || q.status === "failed") && (
                    <Link
                      to={`/reports/${q.id}`}
                      className="text-[var(--ces-red,#C41E3A)] hover:underline text-[13.5px] font-medium"
                    >
                      View →
                    </Link>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ─── CorrectionStore ──────────────────────────────────────────────────────────

const FIELD_OPTIONS = ["All fields", "type", "section", "notes", "mmd", "density"];

function CorrectionStore({
  items,
  loading,
  fieldFilter,
  onFieldFilter,
}: {
  items: Correction[];
  loading: boolean;
  fieldFilter: string;
  onFieldFilter: (v: string) => void;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <select
          value={fieldFilter}
          onChange={(e) => onFieldFilter(e.target.value)}
          className="h-9 px-3 text-[14px] border border-gray-200 rounded bg-white text-gray-700 focus:outline-none focus:ring-1 focus:ring-red-500"
        >
          {FIELD_OPTIONS.map((o) => (
            <option key={o} value={o === "All fields" ? "" : o}>
              {o === "" ? "All fields" : o.charAt(0).toUpperCase() + o.slice(1)}
              {o === "All fields" ? "" : ""}
            </option>
          ))}
        </select>
        <div className="ml-auto text-[14px] text-gray-500">
          <span className="font-semibold text-gray-900">{items.length}</span> corrections · feed keyword rules engine
        </div>
      </div>
      {loading ? (
        <LoadingTable cols={7} />
      ) : (
        <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
          <table className="w-full text-[15px]">
            <thead className="bg-gray-50 text-[13px] uppercase tracking-wider font-bold text-gray-500">
              <tr>
                <th className="text-left px-4 py-2.5 w-24">Field</th>
                <th className="text-left px-4 py-2.5">Original → Corrected</th>
                <th className="text-left px-4 py-2.5 w-1/3">Reason</th>
                <th className="text-left px-4 py-2.5 w-32">DDR</th>
                <th className="text-left px-4 py-2.5 w-32">When</th>
                <th className="text-left px-4 py-2.5 w-28">User</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400 text-[14px]">
                    No corrections logged yet
                  </td>
                </tr>
              )}
              {items.map((c) => (
                <tr key={c.id} className="border-t border-gray-100 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <span className="text-[13px] font-semibold uppercase tracking-wider text-gray-700">
                      {c.field_name}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {c.field_name === "type" ? (
                        <>
                          <TypeBadge type={c.original_value ?? "?"} />
                          <span className="text-gray-400">→</span>
                          <TypeBadge type={c.corrected_value ?? "?"} />
                        </>
                      ) : c.field_name === "section" ? (
                        <>
                          <SectionBadge section={c.original_value} />
                          <span className="text-gray-400">→</span>
                          <SectionBadge section={c.corrected_value} />
                        </>
                      ) : (
                        <>
                          <span className="text-gray-500 line-through truncate max-w-[150px]">
                            {c.original_value ?? "—"}
                          </span>
                          <span className="text-gray-400 shrink-0">→</span>
                          <span className="font-medium truncate max-w-[180px]">{c.corrected_value ?? "—"}</span>
                        </>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-700 text-[14px] leading-5">
                    <div
                      className="overflow-hidden"
                      style={{
                        display: "-webkit-box",
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                      }}
                    >
                      {c.reason ?? "—"}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-[13px] text-gray-500 font-mono">
                    {c.ddr_id.slice(0, 8)}…
                  </td>
                  <td className="px-4 py-3 text-[13.5px] text-gray-500">{fmtTs(c.created_at)}</td>
                  <td className="px-4 py-3 text-[13.5px] text-gray-700">{c.user_id ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── LoadingTable skeleton ────────────────────────────────────────────────────

function LoadingTable({ cols }: { cols: number }) {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      {[...Array(5)].map((_, i) => (
        <div key={i} className={cn("flex gap-3 px-3 py-3", i > 0 && "border-t border-gray-100")}>
          {[...Array(cols)].map((_, j) => (
            <div key={j} className="h-3 bg-gray-100 rounded animate-pulse flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

// ─── Tab bar ──────────────────────────────────────────────────────────────────

type Tab = "pipeline" | "corrections";

// ─── MonitorPage ──────────────────────────────────────────────────────────────

export default function MonitorPage() {
  const [metrics, setMetrics] = useState<MonitorMetrics | null>(null);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [corrections, setCorrections] = useState<Correction[]>([]);
  const [fieldFilter, setFieldFilter] = useState("");
  const [tab, setTab] = useState<Tab>("pipeline");
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [loadingCorrections, setLoadingCorrections] = useState(false);

  const loadMetricsAndQueue = useCallback(async (silent = false) => {
    if (!silent) {
      setLoadingMetrics(true);
      setLoadingQueue(true);
    }
    const [m, q] = await Promise.all([
      apiClient.getMonitorMetrics().catch(() => null),
      apiClient.getMonitorQueue().catch(() => []),
    ]);
    setMetrics(m);
    setQueue(q ?? []);
    setLoadingMetrics(false);
    setLoadingQueue(false);
  }, []);

  const loadCorrections = useCallback(async (field: string) => {
    setLoadingCorrections(true);
    const data = await apiClient.getMonitorCorrections(field || undefined).catch(() => []);
    setCorrections(data);
    setLoadingCorrections(false);
  }, []);

  useEffect(() => {
    void loadMetricsAndQueue();
  }, [loadMetricsAndQueue]);

  useEffect(() => {
    if (tab === "corrections") void loadCorrections(fieldFilter);
  }, [tab, fieldFilter, loadCorrections]);

  const handleFieldFilter = (v: string) => {
    setFieldFilter(v);
  };

  const activeCount = queue.filter((q) => q.status === "processing" || q.status === "queued").length;

  useEffect(() => {
    if (activeCount === 0) {
      return;
    }
    const interval = setInterval(() => {
      void loadMetricsAndQueue(true);
    }, 3000);
    return () => clearInterval(interval);
  }, [activeCount, loadMetricsAndQueue]);

  const tabs: { k: Tab; l: string; n: number | null }[] = [
    { k: "pipeline", l: "Processing queue", n: activeCount },
    { k: "corrections", l: "Correction store", n: corrections.length },
  ];

  return (
    <main className="flex-1 overflow-auto">
      <div className="px-8 py-6 max-w-[1500px] mx-auto">
        {/* Header */}
        <div className="flex items-end justify-between mb-5">
          <div>
            <div className="text-[12px] uppercase tracking-wider font-semibold text-gray-500">Platform admin</div>
            <h1 className="text-[24px] font-bold tracking-tight text-gray-900">Pipeline monitor</h1>
            <p className="text-[14px] text-gray-500 mt-1">
              Extraction pipeline health · correction store.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                void loadMetricsAndQueue();
                if (tab === "corrections") void loadCorrections(fieldFilter);
              }}
              className="flex items-center gap-1.5 h-8 px-3 text-[13px] text-gray-600 border border-gray-200 rounded hover:bg-gray-50 transition-colors"
            >
              <RefreshCwIcon size={13} />
              Refresh
            </button>
          </div>
        </div>

        {/* Metric grid — row 1 */}
        <div className="grid grid-cols-4 gap-2.5">
          <BigMetric
            label="DDRs processed"
            value={loadingMetrics ? "—" : (metrics?.ddrs_this_week ?? 0)}
            sub="this week"
          />
          <BigMetric
            label="Occurrences extracted"
            value={loadingMetrics ? "—" : (metrics?.occurrences_extracted ?? 0).toLocaleString()}
            sub="this week"
          />
          <BigMetric
            label="AI cost"
            value={loadingMetrics ? "—" : fmtMoney(metrics?.ai_cost_weekly ?? 0)}
            sub="weekly"
            delta={
              metrics && metrics.ddrs_this_week > 0
                ? `$${(metrics.ai_cost_weekly / metrics.ddrs_this_week).toFixed(3)} / DDR avg`
                : undefined
            }
          />
          <BigMetric
            label="Corrections logged"
            value={loadingMetrics ? "—" : (metrics?.corrections_this_week ?? 0)}
            sub="this week"
            delta={
              metrics && metrics.occurrences_extracted > 0
                ? `${((metrics.corrections_this_week / metrics.occurrences_extracted) * 100).toFixed(1)}% of rows`
                : undefined
            }
            tone="edit"
          />
        </div>

        {/* Metric grid — row 2 */}
        <div className="grid grid-cols-4 gap-2.5 mt-2.5">
          <BigMetric
            label="Failed dates"
            value={loadingMetrics ? "—" : (metrics?.failed_dates ?? 0)}
            tone={metrics && metrics.failed_dates > 0 ? "failed" : "neutral"}
            sub="open"
          />
          <BigMetric
            label="Avg processing"
            value={loadingMetrics ? "—" : `${metrics?.avg_processing_seconds ?? 0}s`}
            sub="per DDR"
          />
          <BigMetric
            label="Exports"
            value={loadingMetrics ? "—" : (metrics?.exports_this_week ?? 0)}
            sub="this week"
          />
          <BigMetric
            label="Uptime"
            value={loadingMetrics ? "—" : `${metrics?.uptime_month ?? 100}%`}
            sub="last 30 days"
            delta="SLA: 99%"
            tone={metrics && metrics.uptime_month >= 99 ? "success" : "failed"}
          />
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 flex items-center gap-0 mt-7 mb-4">
          {tabs.map((t) => {
            const active = tab === t.k;
            return (
              <button
                key={t.k}
                onClick={() => setTab(t.k)}
                className={cn(
                  "relative h-10 px-4 flex items-center gap-2 text-[15px] font-semibold transition-colors",
                  active ? "text-[var(--ces-red,#C41E3A)]" : "text-gray-500 hover:text-gray-900",
                )}
              >
                {t.l}
                {t.n !== null && (
                  <span
                    className={cn(
                      "px-2 py-0.5 rounded text-[13px] font-bold",
                      active
                        ? "bg-red-50 text-red-700"
                        : "bg-gray-100 text-gray-500",
                    )}
                  >
                    {t.n}
                  </span>
                )}
                {active && (
                  <span className="absolute -bottom-px left-2 right-2 h-[2px] bg-[var(--ces-red,#C41E3A)] rounded-full" />
                )}
              </button>
            );
          })}
        </div>

        {tab === "pipeline" && <PipelineQueue items={queue} loading={loadingQueue} />}
        {tab === "corrections" && (
          <CorrectionStore
            items={corrections}
            loading={loadingCorrections}
            fieldFilter={fieldFilter}
            onFieldFilter={handleFieldFilter}
          />
        )}
      </div>
    </main>
  );
}
