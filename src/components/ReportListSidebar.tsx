import { useEffect, useState } from "react";
import { ChevronLeft as ChevronIcon, Plus as PlusIcon } from "lucide-react";
import { Link, useLocation } from "react-router";

import { useUploadModal } from "@/components/UploadModalContext";
import { apiClient, type DDRDetail } from "@/lib/api";
import { cn } from "@/lib/utils";

function StatusDot({ status, pulse = false }: { status: string; pulse?: boolean }) {
  const colorMap: Record<string, string> = {
    success: "bg-emerald-500",
    complete: "bg-emerald-500",
    processing: "bg-blue-500",
    queued: "bg-slate-400",
    failed: "bg-red-500",
    warning: "bg-amber-500",
  };
  const color = colorMap[status] ?? "bg-slate-400";
  return (
    <span className="relative inline-flex h-2 w-2 shrink-0">
      {pulse && <span className={cn("absolute inset-0 rounded-full opacity-30 animate-pulse", color)} />}
      <span className={cn("relative inline-block h-2 w-2 rounded-full", color)} />
    </span>
  );
}

export default function ReportListSidebar({ selectedId, reports: propReports }: { selectedId?: string; reports?: DDRDetail[] }) {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem("ces-report-sidebar-collapsed") === "true";
    } catch {
      return false;
    }
  });
  const [fetchedReports, setFetchedReports] = useState<DDRDetail[]>([]);
  const [loading, setLoading] = useState(propReports === undefined);
  const [lastSync, setLastSync] = useState<string>("");
  const { setOpen } = useUploadModal();
  const location = useLocation();

  const reports = propReports ?? fetchedReports;

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem("ces-report-sidebar-collapsed", String(next));
  };

  useEffect(() => {
    if (propReports !== undefined) return;
    let active = true;
    setLoading(true);
    apiClient
      .listDDRs()
      .then((items) => {
        if (active) {
          setFetchedReports(items);
          setLoading(false);
          setLastSync("last sync just now");
        }
      })
      .catch(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [propReports]);

  const isActive = (reportId: string) => {
    if (selectedId) return reportId === selectedId;
    return false;
  };

  const failedCount = (ddr: DDRDetail) =>
    ddr.dates?.filter((d) => d.status === "failed").length ?? 0;

  const processedCount = (ddr: DDRDetail) =>
    ddr.dates?.filter((d) => d.status !== "queued").length ?? 0;

  const totalCount = (ddr: DDRDetail) => ddr.dates?.length ?? 0;

  const fileName = (path: string) => path.split("/").at(-1) ?? path;

  return (
    <aside
      className={cn(
        "shrink-0 sticky top-14 flex flex-col border-r border-border-default bg-surface transition-[width] duration-200 h-[calc(100vh-3.5rem)]",
        collapsed ? "w-12" : "w-[260px]"
      )}
    >
      <div className="flex-1 overflow-auto">
        {!collapsed && (
          <div className="p-3">
            <button
              onClick={() => setOpen(true)}
              className="inline-flex items-center justify-center gap-1.5 w-full h-8 px-3 rounded-md text-[12px] font-semibold bg-white border border-ces-red text-ces-red hover:bg-ces-red-light/20 transition-colors"
              aria-label="New upload"
            >
              <PlusIcon className="w-3.5 h-3.5" aria-hidden="true" />
              New upload
            </button>
            <div className="mt-3 flex items-center gap-2 text-[10.5px] uppercase tracking-wider font-semibold text-text-muted">
              <span>Reports</span>
              <span className="ml-auto text-text-muted font-normal normal-case">Today</span>
            </div>
          </div>
        )}

        {collapsed && (
          <div className="pt-2 flex justify-center">
            <button
              onClick={() => setOpen(true)}
              className="h-8 w-8 grid place-items-center rounded-md bg-white border border-ces-red text-ces-red hover:bg-ces-red-light/20 transition-colors"
              title="New upload"
            >
              <PlusIcon className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        <div className="flex flex-col">
          {loading && !collapsed && (
            <div className="px-3 py-2 text-[11px] text-text-muted">Loading…</div>
          )}

          {reports.map((r) => {
            const active = isActive(r.id);
            const failed = failedCount(r);
            const processed = processedCount(r);
            const total = totalCount(r);
            const isProcessing = r.status === "processing";

            if (collapsed) {
              return (
                <Link
                  key={r.id}
                  to={`/reports/${r.id}`}
                  className={cn(
                    "w-full h-10 grid place-items-center hover:bg-white relative transition-colors",
                    active && "bg-ces-red-light/30"
                  )}
                  title={fileName(r.file_path)}
                >
                  <StatusDot status={r.status} pulse={isProcessing} />
                  {active && (
                    <span className="absolute inset-y-0 left-0 right-0 bg-ces-red-light/20 rounded-md -z-10" />
                  )}
                </Link>
              );
            }

            return (
              <Link
                key={r.id}
                to={`/reports/${r.id}`}
                className={cn(
                  "w-full text-left px-3 py-2.5 flex items-start gap-2.5 transition-colors",
                  active
                    ? "bg-ces-red-light/30"
                    : "hover:bg-white"
                )}
              >
                <div className="pt-1">
                  <StatusDot status={r.status} pulse={isProcessing} />
                </div>
                <div className="flex-1 min-w-0">
                  <div
                    className={cn(
                      "text-[12.5px] font-semibold truncate",
                      active ? "text-ces-red-dark" : "text-text-primary"
                    )}
                  >
                    {fileName(r.file_path)}
                  </div>
                  <div className="text-[11px] text-text-muted truncate mt-0.5">
                    {r.well_name ?? "—"} · {r.dates?.length ?? 0} occ
                  </div>
                  {isProcessing && total > 0 && (
                    <div className="mt-1.5 h-1 bg-border-default rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500"
                        style={{ width: `${(processed / total) * 100}%` }}
                      />
                    </div>
                  )}
                </div>
                {failed > 0 && (
                  <span className="px-1.5 py-0 rounded text-[10px] font-bold bg-ces-red text-white shrink-0 mt-0.5">
                    {failed}
                  </span>
                )}
              </Link>
            );
          })}

          {!loading && reports.length === 0 && !collapsed && (
            <div className="px-3 py-4 text-[11px] text-text-muted text-center">
              No reports yet
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-border-default flex items-center px-2 py-2">
        {!collapsed && (
          <div className="text-[10.5px] text-text-muted px-1">
            <span className="font-semibold text-text-secondary">{reports.length}</span> reports
            {lastSync && <span className="ml-1">· {lastSync}</span>}
          </div>
        )}
        <button
          onClick={toggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="ml-auto h-9 w-9 grid place-items-center text-text-muted hover:text-text-primary hover:bg-white rounded-md transition-colors shrink-0"
        >
          <ChevronIcon
            className={cn("w-4 h-4 transition-transform", collapsed ? "" : "rotate-180")}
          />
        </button>
      </div>
    </aside>
  );
}
