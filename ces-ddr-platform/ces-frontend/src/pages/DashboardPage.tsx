import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";

import DDRUploadPanel from "@/components/DDRUploadPanel";
import { Button } from "@/components/ui/button";
import { apiClient, type DDRDetail } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function DashboardPage() {
  const navigate = useNavigate();
  const [ddrs, setDdrs] = useState<DDRDetail[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let active = true;

    void apiClient
      .listDDRs()
      .then((items) => {
        if (active) {
          setDdrs(items);
          setLoadState("ready");
        }
      })
      .catch(() => {
        if (active) {
          setLoadState("error");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const activeCount = ddrs.filter((ddr) => ddr.status === "queued" || ddr.status === "processing").length;
  const failedCount = ddrs.filter((ddr) => ddr.status === "failed").length;
  const completeCount = ddrs.filter((ddr) => ddr.status === "complete").length;
  const recentHeading = {
    loading: "Loading DDRs",
    error: "DDR list unavailable",
    ready:
      ddrs.length === 0
        ? "No DDRs uploaded"
        : `${ddrs.length} DDR${ddrs.length === 1 ? "" : "s"} loaded `,
  }[loadState];
  const recentEyebrow = {
    loading: "Backend request pending",
    error: "Backend request failed",
    ready:
      activeCount > 0
        ? `${activeCount} active, ${completeCount} complete, ${failedCount} failed`
        : `${completeCount} complete, ${failedCount} failed`,
  }[loadState];

  const statusColor = (status: string) => {
    switch (status) {
      case "processing":
      case "queued":
        return "text-[#92400E]";
      case "complete":
        return "text-[#047857]";
      case "failed":
        return "text-error-text";
      default:
        return "text-text-muted";
    }
  };

  return (
    <section className="grid gap-7 animate-fade-in-up">
      <div className="grid grid-cols-3 gap-4 max-[760px]:grid-cols-1" aria-label="DDR queue summary">
        <article className="relative min-h-[108px] p-5 pb-4 border border-border-default rounded-xl bg-white overflow-hidden transition-all duration-300 ease-out-quart hover:-translate-y-[3px] hover:shadow-[0_1px_2px_rgba(0,0,0,0.04),0_8px_24px_rgba(0,0,0,0.06)] animate-fade-in-up" style={{ animationDelay: "0.05s" }}>
          <span className="block mb-3 text-text-muted text-[13px]">Active DDRs</span>
          <strong className="block mt-2.5 text-4xl leading-none tracking-tight animate-count-pop">{loadState === "ready" ? activeCount : "-"}</strong>
        </article>
        <article className="relative min-h-[108px] p-5 pb-4 border border-border-default rounded-xl bg-white overflow-hidden transition-all duration-300 ease-out-quart hover:-translate-y-[3px] hover:shadow-[0_1px_2px_rgba(0,0,0,0.04),0_8px_24px_rgba(0,0,0,0.06)] animate-fade-in-up" style={{ animationDelay: "0.1s" }}>
          <span className="block mb-3 text-text-muted text-[13px]">Completed</span>
          <strong className="block mt-2.5 text-4xl leading-none tracking-tight animate-count-pop">{loadState === "ready" ? completeCount : "-"}</strong>
        </article>
        <article className="relative min-h-[108px] p-5 pb-4 border border-border-default rounded-xl bg-white overflow-hidden transition-all duration-300 ease-out-quart hover:-translate-y-[3px] hover:shadow-[0_1px_2px_rgba(0,0,0,0.04),0_8px_24px_rgba(0,0,0,0.06)] animate-fade-in-up" style={{ animationDelay: "0.15s" }}>
          <span className="block mb-3 text-text-muted text-[13px]">Failed</span>
          <strong className="block mt-2.5 text-4xl leading-none tracking-tight animate-count-pop">{loadState === "ready" ? failedCount : "-"}</strong>
        </article>
      </div>

      <div className="grid grid-cols-[1fr_minmax(280px,360px)] gap-5 items-start max-[760px]:grid-cols-1">
        <section className="p-5 border border-border-default rounded-lg bg-white" aria-label="Recent DDRs">
          <div className="flex items-start justify-between gap-4 mb-[18px] max-[760px]:flex-col">
            <div>
              <p className="m-0 mb-1 text-ces-red text-[11px] font-bold tracking-[0.06em] uppercase">{recentEyebrow}</p>
              <h2 className="m-0 text-[22px] leading-snug font-semibold">{recentHeading}</h2>
            </div>
            <Button asChild variant="outline">
              <Link to="/monitor">Monitor queue</Link>
            </Button>
          </div>

          {loadState === "loading" ? <p className="text-text-muted">Loading DDRs...</p> : null}
          {loadState === "error" ? <p className="m-0 px-3 py-2.5 rounded-lg text-error-text bg-error-bg text-[13px] font-semibold">Unable to load DDRs</p> : null}
          {loadState === "ready" && ddrs.length === 0 ? (
            <div className="grid place-items-center gap-3.5 py-10 px-6 border-[1.5px] border-dashed border-border-input rounded-xl text-center" style={{ background: "radial-gradient(ellipse 80% 50% at 50% 100%, rgba(196,18,48,0.04) 0%, transparent 60%), #F9FAFB" }}>
              <svg className="w-12 h-12 text-text-muted opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="12" y1="18" x2="12" y2="12" />
                <line x1="9" y1="15" x2="15" y2="15" />
              </svg>
              <strong className="text-text-secondary text-[15px] font-semibold">No DDRs uploaded yet</strong>
              <p className="m-0 max-w-[320px] leading-relaxed text-text-muted">Start with a field DDR PDF and track extraction status from the report page.</p>
            </div>
          ) : null}

          {ddrs.length > 0 ? (
            <div className="grid border border-border-default rounded-xl overflow-hidden bg-white" role="table" aria-label="Recent DDR list">
              <div className="relative grid grid-cols-[minmax(160px,1fr)_120px_120px_64px] gap-3 items-center min-h-11 px-[18px] py-0 bg-[#F8F9FA] text-text-muted text-[11px] font-bold uppercase tracking-wider max-[760px]:grid-cols-1" role="row">
                <span>File</span>
                <span>Status</span>
                <span>Created</span>
                <span />
              </div>
              {ddrs.slice(0, 8).map((ddr) => (
                <div className="relative grid grid-cols-[minmax(160px,1fr)_120px_120px_64px] gap-3 items-center min-h-[52px] px-[18px] py-0 border-t border-border-default text-sm transition-colors duration-200 hover:bg-[#FAFBFC] max-[760px]:grid-cols-1" role="row" key={ddr.id}>
                  <span>{ddr.file_path.split("/").at(-1) ?? ddr.file_path}</span>
                  <strong className={cn("inline-flex items-center gap-1.5 capitalize text-[13px] font-semibold", statusColor(ddr.status))}>{ddr.status}</strong>
                  <span>{new Date(ddr.created_at * 1000).toLocaleDateString()}</span>
                  <Link to={`/reports/${ddr.id}`} className="text-ces-red font-semibold text-[13px] no-underline transition-colors duration-200 hover:text-ces-red-dark hover:underline underline-offset-[3px]">View</Link>
                </div>
              ))}
            </div>
          ) : null}
        </section>

        <DDRUploadPanel
          onUploaded={(created, file) => {
            setDdrs((current) => [
              {
                id: created.id,
                file_path: file.name,
                status: created.status,
                created_at: Math.floor(Date.now() / 1000),
              },
              ...current,
            ]);
            setLoadState("ready");
            navigate(`/reports/${created.id}`);
          }}
        />
      </div>
    </section>
  );
}
