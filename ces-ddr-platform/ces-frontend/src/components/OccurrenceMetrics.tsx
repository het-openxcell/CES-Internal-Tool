import { useMemo } from "react";

import { TypeBadge } from "@/components/TypeBadge";
import type { OccurrenceRow } from "@/lib/api";

const CRITICAL_TYPES = new Set([
  "Kick / Well Control",
  "Blowout",
  "H2S",
  "Stuck Pipe",
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
      accent: metrics.critical > 0 ? "text-red-600" : "text-text-primary",
    },
    {
      label: "Max Depth Hit",
      value: metrics.maxDepth ?? "—",
      unit: metrics.maxDepth != null ? "m" : "",
      accent: "text-text-primary",
    },
    {
      label: "Avg Depth",
      value: metrics.avgDepth ?? "—",
      unit: metrics.avgDepth != null ? "m" : "",
      accent: "text-text-primary",
    },
  ];

  return (
    <section aria-label="Occurrence metrics">
      <div className="grid grid-cols-4 gap-4 max-[900px]:grid-cols-2 max-[500px]:grid-cols-1">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-xl border border-border-default bg-white px-5 py-4"
          >
            <p className="m-0 mb-1 text-[10px] font-bold uppercase tracking-widest text-text-muted">
              {card.label}
            </p>
            <p
              className={`m-0 text-[28px] font-black leading-none tabular-nums ${card.accent}`}
            >
              {card.value}
              {card.unit && (
                <span className="ml-1 text-sm font-semibold text-text-muted">
                  {card.unit}
                </span>
              )}
            </p>
          </div>
        ))}
      </div>

      {metrics.topIssue && (
        <div className="mt-3 rounded-xl border border-border-default bg-white px-5 py-3 flex items-center gap-3">
          <span className="text-[10px] font-bold uppercase tracking-widest text-text-muted">
            Top Issue
          </span>
          <TypeBadge type={metrics.topIssue.type} />
          <span className="text-sm font-semibold text-text-muted">
            {metrics.topIssue.count} occurrence
            {metrics.topIssue.count !== 1 ? "s" : ""}
          </span>
        </div>
      )}
    </section>
  );
}
