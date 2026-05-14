import { useEffect, useState } from "react";
import { useNavigate } from "react-router";

import ReportListSidebar from "@/components/ReportListSidebar";
import { apiClient, type DDRDetail } from "@/lib/api";

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
          if (items.length > 0) {
            navigate(`/reports/${items[0].id}`, { replace: true });
          }
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
  }, [navigate]);

  return (
    <>
      <ReportListSidebar reports={ddrs} />
      <main className="flex-1 min-w-0 overflow-auto">
        <div className="px-8 py-6 max-w-[1400px] mx-auto animate-fade-in-up">
          <div className="flex items-center justify-between gap-6 pb-6 border-b border-border-default max-[760px]:flex-col max-[760px]:items-start">
            <div>
              <p className="m-0 mb-1 text-ces-red text-[11px] font-bold tracking-[0.06em] uppercase">Canadian Energy Services</p>
              <h1 className="m-0 text-[28px] leading-tight font-bold text-text-primary tracking-tight">DDR Processing</h1>
            </div>
          </div>

          <section className="mt-6 p-5 border border-border-default rounded-lg bg-white" aria-label="Recent DDRs">
            {loadState === "loading" ? (
              <div className="py-8 text-center text-text-muted">Loading DDRs...</div>
            ) : null}
            {loadState === "error" ? (
              <div className="py-8">
                <p className="m-0 mb-1 text-ces-red text-[11px] font-bold tracking-[0.06em] uppercase">Backend request failed</p>
                <h2 className="m-0 text-[22px] leading-snug font-semibold mb-3">DDR list unavailable</h2>
                <p className="m-0 px-3 py-2.5 rounded-lg text-error-text bg-error-bg text-[13px] font-semibold">Unable to load DDRs</p>
              </div>
            ) : null}
            {loadState === "ready" && ddrs.length === 0 ? (
              <div className="py-8 text-center">
                <p className="m-0 mb-1 text-ces-red text-[11px] font-bold tracking-[0.06em] uppercase">Reports</p>
                <h2 className="m-0 text-[22px] leading-snug font-semibold mb-2">No reports yet</h2>
                <p className="text-text-muted text-sm">Upload a DDR PDF to get started.</p>
              </div>
            ) : null}
          </section>
        </div>
      </main>
    </>
  );
}
