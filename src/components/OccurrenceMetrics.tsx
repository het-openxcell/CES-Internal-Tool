import { useMemo } from "react";

import { TypeBadge } from "@/components/TypeBadge";
import type { OccurrenceRow } from "@/lib/api";

const CRITICAL_TYPES = new Set([
  "Kick / Well Control",
  "Blowout",
  "H2S",
  "Stuck Pipe",
  "Lost Circulation",
  "Tight Hole",
]);

function computeMetrics(occurrences: OccurrenceRow[]) {
  if (occurrences.length === 0) {
    return {
      total: 0,
      critical: 0,
      maxDepth: null as number | null,
      avgDepth: null as number | null,
      topIssue: null as { type: string; count: number } | null,
    };
  }

  const critical = occurrences.filter((o) => CRITICAL_TYPES.has(o.type)).length;

  const depths = occurrences
    .map((o) => o.mmd)
    .filter((v): v is number => v != null);
  const maxDepth = depths.length > 0 ? Math.max(...depths) : null;
  const avgDepth =
    depths.length > 0
      ? Math.round((depths.reduce((a, b) => a + b, 0) / depths.length) * 10) / 10
      : null;

  const typeCounts = new Map<string, number>();
  for (const o of occurrences) {
    typeCounts.set(o.type, (typeCounts.get(o.type) ?? 0) + 1);
  }
  let topIssue: { type: string; count: number } | null = null;
  for (const [type, count] of typeCounts) {
    if (!topIssue || count > topIssue.count) {
      topIssue = { type, count };
    }
  }

  return {
    total: occurrences.length,
    critical,
    maxDepth,
    avgDepth,
    topIssue,
  };
}

export type OccurrenceMetricsProps = {
  occurrences: OccurrenceRow[];
};

export function OccurrenceMetrics({ occurrences }: OccurrenceMetricsProps) {
  const metrics = useMemo(() => computeMetrics(occurrences), [occurrences]);

  const cards = [
    {
      label: "Total Occurrences",
      value: metrics.total,
      unit: "",
      accent: "text-text-primary",
    },
    {
      label: "Critical Incidents",
      value: metrics.critical,
      unit: "",
      accent: metrics.critical > 0 ? "text-ces-red" : "text-text-primary",
    },
    {
      label: "Max Depth Hit",
      value: metrics.maxDepth ?? "—",
      unit: metrics.maxDepth != null ? "mMD" : "",
      accent: "text-text-primary",
    },
    {
      label: "Avg Depth",
      value: metrics.avgDepth ?? "—",
      unit: metrics.avgDepth != null ? "mMD" : "",
      accent: "text-text-primary",
    },
  ];

  return (
    <section aria-label="Occurrence metrics">
      <div className="grid grid-cols-4 gap-3 max-[900px]:grid-cols-2 max-[500px]:grid-cols-1">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-lg border border-border-default bg-white px-4 py-3 shadow-[0_1px_2px_rgba(0,0,0,0.04),0_4px_8px_rgba(0,0,0,0.03)]"
          >
            <p className="m-0 text-[10.5px] font-bold uppercase tracking-wider text-text-muted">
              {card.label}
            </p>
            <div className="flex items-baseline gap-1.5 mt-1">
              <p className={`m-0 text-[28px] font-bold tracking-tight leading-none tabular-nums ${card.accent}`}>
                {card.value}
              </p>
              {card.unit && (
                <span className="text-[12px] text-text-muted font-medium">
                  {card.unit}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {metrics.topIssue && (
        <div className="mt-3 bg-surface border border-border-default rounded-lg px-4 py-2.5 flex items-center gap-3">
          <span className="text-[10.5px] font-bold uppercase tracking-wider text-ces-red">
            Top Issue
          </span>
          <TypeBadge type={metrics.topIssue.type} />
          <span className="text-[12.5px] text-text-muted">
            <span className="font-semibold text-text-primary">{metrics.topIssue.count}</span> occurrence
            {metrics.topIssue.count !== 1 ? "s" : ""} flagged this report
          </span>
          <button className="ml-auto text-[12px] font-medium text-ces-red hover:underline">
            Show only these →
          </button>
        </div>
      )}
    </section>
  );
}
