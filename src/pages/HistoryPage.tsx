import { type ReactNode, useEffect, useState } from "react";

import { apiClient, type HistoryOccurrenceRow } from "@/lib/api";
import { SectionBadge } from "@/components/SectionBadge";
import { TypeBadge } from "@/components/TypeBadge";
import { cn } from "@/lib/utils";

type FilterOption = {
  label: string;
  tone: string;
};

const OCCURRENCE_TYPES: FilterOption[] = [
  { label: "Drilling", tone: "bg-blue-100 text-blue-800 border-blue-200" },
  { label: "Tripping", tone: "bg-sky-100 text-sky-800 border-sky-200" },
  { label: "Ream", tone: "bg-emerald-100 text-emerald-800 border-emerald-200" },
  { label: "Back Ream", tone: "bg-green-100 text-green-800 border-green-200" },
  { label: "Circulating", tone: "bg-purple-100 text-purple-800 border-purple-200" },
  { label: "BHA Work", tone: "bg-amber-100 text-amber-800 border-amber-200" },
  { label: "Casing", tone: "bg-rose-100 text-rose-800 border-rose-200" },
  { label: "Cementing", tone: "bg-indigo-100 text-indigo-800 border-indigo-200" },
];

const SECTIONS: FilterOption[] = [
  { label: "Surface", tone: "bg-emerald-100 text-emerald-800 border-emerald-200" },
  { label: "Int.", tone: "bg-sky-100 text-sky-800 border-sky-200" },
  { label: "Main", tone: "bg-indigo-100 text-indigo-800 border-indigo-200" },
];

const DEFAULT_TYPES: string[] = [];
const DEFAULT_SECTIONS: string[] = [];

function LayersIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m12 3 8 4-8 4-8-4 8-4Z" />
      <path d="m4 12 8 4 8-4" />
      <path d="m4 17 8 4 8-4" />
    </svg>
  );
}

function DownloadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3v12" />
      <path d="m7 10 5 5 5-5" />
      <path d="M5 21h14" />
    </svg>
  );
}

function FilterBadge({ option }: { option: FilterOption }) {
  return (
    <span className={cn("inline-flex items-center rounded border px-2 py-0.5 text-[12px] font-semibold leading-5", option.tone)}>
      {option.label}
    </span>
  );
}

function FilterCheckbox({ checked, onChange, children }: { checked: boolean; onChange: () => void; children: ReactNode }) {
  return (
    <label className="flex min-h-6 items-center gap-2 text-[14px] text-gray-900">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="h-3.5 w-3.5 rounded border-gray-300 accent-ces-red"
      />
      {children}
    </label>
  );
}

function FilterSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-b border-gray-200 px-3 py-4">
      <h2 className="mb-3 text-[12px] font-bold uppercase tracking-wider text-gray-700">{title}</h2>
      {children}
    </section>
  );
}

function formatDate(value: string | null) {
  if (!value || value.length !== 8) return "—";
  return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
}

function DateCell({ value }: { value: string | null }) {
  if (!value || value.length !== 8) return <span className="text-[14px] text-gray-500">—</span>;
  const ymd = `${value.slice(0, 4)}-${value.slice(4, 6)}-`;
  const day = value.slice(6, 8);
  return (
    <div className="leading-tight">
      <div className="text-[14px] text-gray-700">{ymd}</div>
      <div className="text-[14px] text-gray-700">{day}</div>
    </div>
  );
}

function formatDepth(value: number | null) {
  if (value === null) return "—";
  const num = Number.isInteger(value) ? String(value) : value.toFixed(1);
  return num.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function formatTime(start: string | null, end: string | null) {
  if (start && end) return `${start}–${end}`;
  return start ?? end ?? "—";
}

function FilterChip({ label, value, onRemove }: { label: string; value: string; onRemove?: () => void }) {
  return (
    <span className="inline-flex h-8 items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 text-[13px] text-gray-700">
      <span className="font-semibold text-gray-900">{label}:</span>
      {value}
      {onRemove && (
        <button type="button" onClick={onRemove} className="ml-1 text-gray-400 hover:text-gray-700" aria-label={`Remove ${label} ${value}`}>
          ×
        </button>
      )}
    </span>
  );
}

export default function HistoryPage() {
  const [types, setTypes] = useState<string[]>(DEFAULT_TYPES);
  const [sections, setSections] = useState<string[]>(DEFAULT_SECTIONS);
  const [fromDepth, setFromDepth] = useState(50);
  const [toDepth, setToDepth] = useState(6000);
  const [rows, setRows] = useState<HistoryOccurrenceRow[]>([]);
  const [loading, setLoading] = useState(true);

  const toggle = (value: string, values: string[], setValues: (next: string[]) => void) => {
    setValues(values.includes(value) ? values.filter((item) => item !== value) : [...values, value]);
  };

  const resetFilters = () => {
    setTypes([]);
    setSections([]);
    setFromDepth(50);
    setToDepth(6000);
  };

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    apiClient
      .searchHistoryOccurrences(
        {
          types,
          sections,
          depth_from: fromDepth > 50 ? fromDepth : undefined,
          depth_to: toDepth < 6000 ? toDepth : undefined,
        },
        controller.signal,
      )
      .then(setRows)
      .catch((error: unknown) => {
        if ((error as Error).name !== "AbortError") setRows([]);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [types, sections, fromDepth, toDepth]);

  return (
    <main id="main-content" className="flex min-h-0 flex-1 overflow-hidden bg-white">
      <aside className="flex w-[260px] shrink-0 flex-col border-r border-gray-200 bg-surface">
        <div className="flex h-12 items-center justify-between border-b border-gray-200 px-3">
          <span className="text-[12px] font-bold uppercase tracking-wider text-gray-700">Filters</span>
          <button type="button" onClick={resetFilters} className="text-[12px] font-semibold text-ces-red hover:underline">
            Reset
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <FilterSection title="Occurrence Type">
            <div className="max-h-[178px] space-y-1.5 overflow-y-auto pr-1">
              {OCCURRENCE_TYPES.map((option) => (
                <FilterCheckbox
                  key={option.label}
                  checked={types.includes(option.label)}
                  onChange={() => toggle(option.label, types, setTypes)}
                >
                  <FilterBadge option={option} />
                </FilterCheckbox>
              ))}
            </div>
          </FilterSection>

          <FilterSection title="Section">
            <div className="space-y-1.5">
              {SECTIONS.map((option) => (
                <FilterCheckbox
                  key={option.label}
                  checked={sections.includes(option.label)}
                  onChange={() => toggle(option.label, sections, setSections)}
                >
                  <FilterBadge option={option} />
                </FilterCheckbox>
              ))}
            </div>
          </FilterSection>

          <FilterSection title="Depth Range (MMD)">
            <div className="mb-3 flex items-center justify-between text-[13px] text-gray-500">
              <span>{fromDepth}m</span>
              <span>{toDepth}m</span>
            </div>
            <div className="space-y-2">
              <input
                type="range"
                min={50}
                max={6000}
                step={50}
                value={fromDepth}
                onChange={(event) => setFromDepth(Math.min(Number(event.target.value), toDepth - 50))}
                className="h-1.5 w-full accent-ces-red"
              />
              <input
                type="range"
                min={50}
                max={6000}
                step={50}
                value={toDepth}
                onChange={(event) => setToDepth(Math.max(Number(event.target.value), fromDepth + 50))}
                className="h-1.5 w-full accent-ces-red"
              />
            </div>
          </FilterSection>

        </div>

        <div className="flex h-11 items-center justify-end border-t border-gray-200 px-3 text-[15px] text-gray-400">‹</div>
      </aside>

      <section className="min-w-0 flex-1 overflow-auto">
        <div className="mx-auto max-w-[1452px] px-8 py-6">
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <div className="text-[12px] font-bold uppercase tracking-wider text-gray-500">Research</div>
              <h1 className="mt-1 text-[24px] font-bold tracking-tight text-gray-950">Cross-job history</h1>
              <p className="mt-1 text-[14px] text-gray-500">
                Offset well research across CES's DDR archive. Filter by type, section, depth, operator.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button className="inline-flex h-9 items-center gap-2 rounded-md border border-gray-200 bg-white px-3.5 text-[14px] font-semibold text-gray-700 hover:bg-gray-50">
                <LayersIcon className="h-4 w-4" />
                Group by well
              </button>
              <button className="inline-flex h-9 items-center gap-2 rounded-md bg-ces-red px-3.5 text-[14px] font-semibold text-white hover:bg-ces-red-dark">
                <DownloadIcon className="h-4 w-4" />
                Export CSV
              </button>
            </div>
          </div>

          <div className="mb-4 flex min-h-12 items-center gap-2 rounded-lg border border-gray-200 bg-surface px-3 py-2">
            <span className="mr-1 text-[12px] font-bold uppercase tracking-wider text-gray-500">Active Filters</span>
            {types.length === 0 && sections.length === 0 && fromDepth === 50 && toDepth === 6000 && (
              <span className="text-[14px] text-gray-500">All history</span>
            )}
            {types.map((type) => (
              <FilterChip key={type} label="Type" value={type} onRemove={() => setTypes(types.filter((item) => item !== type))} />
            ))}
            {sections.map((section) => (
              <FilterChip key={section} label="Section" value={section} onRemove={() => setSections(sections.filter((item) => item !== section))} />
            ))}
            {(fromDepth !== 50 || toDepth !== 6000) && <FilterChip label="Depth" value={`${fromDepth} – ${toDepth} m`} />}
            <div className="ml-auto whitespace-nowrap text-[14px] text-gray-500">
              <span className="font-bold text-gray-950">{loading ? "—" : rows.length}</span> occurrences match
            </div>
          </div>

          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <div className="max-h-[640px] overflow-auto">
              <table className="w-full text-[15px]">
                <thead className="sticky top-0 z-10 bg-surface text-[13px] font-bold uppercase tracking-wider text-gray-500">
                  <tr>
                    <th className="w-24 px-4 py-2.5 text-left">Date</th>
                    <th className="w-20 px-4 py-2.5 text-left">Time</th>
                    <th className="w-28 px-4 py-2.5 text-left">Section</th>
                    <th className="w-36 px-4 py-2.5 text-left">Type</th>
                    <th className="px-4 py-2.5 text-left">Well</th>
                    <th className="w-32 px-4 py-2.5 text-right">From (MMD)</th>
                    <th className="w-28 px-4 py-2.5 text-right">To (MMD)</th>
                    <th className="w-[42%] px-4 py-2.5 text-left">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {loading && (
                    <tr>
                      <td colSpan={8} className="px-4 py-12 text-center text-[14px] text-gray-400">
                        Loading history…
                      </td>
                    </tr>
                  )}
                  {!loading && rows.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-4 py-12 text-center text-[14px] text-gray-400">
                        No occurrence history matches the selected filters
                      </td>
                    </tr>
                  )}
                  {!loading && rows.map((row) => (
                    <tr key={row.id} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-2">
                        <DateCell value={row.date} />
                      </td>
                      <td className="px-4 py-2 text-[14px] text-gray-500">—</td>
                      <td className="px-4 py-2">{row.section ? <SectionBadge section={row.section} /> : <span className="text-[14px] text-gray-500">—</span>}</td>
                      <td className="px-4 py-2"><TypeBadge type={row.type} /></td>
                      <td className="px-4 py-2">
                        <div className="text-[14px] font-medium text-gray-900">{row.well_name ?? "Unknown well"}</div>
                        <div className="text-[13px] text-gray-500">{row.operator ?? row.area ?? row.surface_location ?? "—"}</div>
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-[14px] text-gray-700">{formatDepth(row.from_mmd)}</td>
                      <td className="px-4 py-2 text-right font-mono text-[14px] text-gray-700">{formatDepth(row.to_mmd)}</td>
                      <td className="px-4 py-2 text-[14px] leading-5 text-gray-700">{row.notes ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
