import { useMemo, useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";

import { TypeBadge } from "@/components/TypeBadge";
import { SectionBadge } from "@/components/SectionBadge";

import { EmptyState } from "@/components/ui/empty-state";
import { cn } from "@/lib/utils";
import type { OccurrenceRow } from "@/lib/api";

const ALL_TYPES = [
  "Stuck Pipe",
  "Lost Circulation",
  "Back Ream",
  "Ream",
  "Tight Hole",
  "Washout",
  "BHA Failure",
  "Vibration",
  "Kick / Well Control",
  "H2S",
  "Deviation",
  "Fishing",
  "Pack Off",
  "Casing Issue",
  "Cementing Issue",
  "Bit Failure",
];

const ALL_SECTIONS = ["Surface", "Int.", "Main"];

const columns: ColumnDef<OccurrenceRow>[] = [
  { accessorKey: "date", header: "Incident Date", enableHiding: true },
  {
    accessorKey: "type",
    header: "Type",
    cell: ({ getValue }) => {
      const v = (getValue() as string | null) ?? "Unknown";
      return <TypeBadge type={v} />;
    },
  },
  {
    accessorKey: "section",
    header: "Section",
    cell: ({ getValue }) => <SectionBadge section={getValue() as string | null} />,
  },
  {
    accessorKey: "mmd",
    header: "MMD",
    cell: ({ getValue }) => (getValue() != null ? (getValue() as number).toFixed(1) : "—"),
  },
  {
    accessorKey: "page_number",
    header: "Page",
    cell: ({ getValue }) => (getValue() != null ? (getValue() as number) : "—"),
  },
  {
    accessorKey: "notes",
    header: "Notes",
    cell: ({ getValue }) => (getValue() as string | null) ?? "—",
  },
];

const VISIBLE_COLUMN_KEYS = ["date", "type", "section", "mmd", "page_number", "notes"];

export type OccurrenceTableProps = {
  occurrences: OccurrenceRow[];
  isLoading: boolean;
};

export function OccurrenceTable({ occurrences, isLoading }: OccurrenceTableProps) {
  const [searchParams, setSearchParams] = useSearchParams();

  const [sorting, setSorting] = useState<SortingState>([{ id: "date", desc: true }]);
  const [globalFilter, setGlobalFilter] = useState(() => searchParams.get("q") ?? "");
  const [typeFilter, setTypeFilter] = useState(() => searchParams.get("type") ?? "");
  const [sectionFilter, setSectionFilter] = useState(() => searchParams.get("section") ?? "");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tbodyRef = useRef<HTMLTableSectionElement>(null);
  const [focusedCell, setFocusedCell] = useState<{ row: number; col: number } | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (typeFilter) next.set("type", typeFilter);
          else next.delete("type");
          if (sectionFilter) next.set("section", sectionFilter);
          else next.delete("section");
          if (globalFilter) next.set("q", globalFilter);
          else next.delete("q");
          return next;
        },
        { replace: true },
      );
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [typeFilter, sectionFilter, globalFilter, setSearchParams]);

  useEffect(() => {
    setTypeFilter(searchParams.get("type") ?? "");
    setSectionFilter(searchParams.get("section") ?? "");
    setGlobalFilter(searchParams.get("q") ?? "");
  }, [searchParams]);

  useEffect(() => {
    if (!focusedCell) return;
    const cell = tbodyRef.current?.querySelector<HTMLElement>(
      `[data-cell-rc="${focusedCell.row}-${focusedCell.col}"]`,
    );
    cell?.focus();
  }, [focusedCell]);

  const filtered = useMemo(() => {
    return occurrences
      .filter((row) => !typeFilter || row.type === typeFilter)
      .filter((row) => !sectionFilter || row.section === sectionFilter)
      .filter((row) => {
        if (!globalFilter) return true;
        const q = globalFilter.toLowerCase();
        return [row.well_name, row.surface_location, row.type, row.section, row.notes, row.page_number?.toString()].some((v) =>
          v?.toLowerCase().includes(q),
        );
      });
  }, [occurrences, typeFilter, sectionFilter, globalFilter]);

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const activeFilters = useMemo(() => {
    const list: { key: string; label: string }[] = [];
    if (typeFilter) list.push({ key: "type", label: `Type: ${typeFilter}` });
    if (sectionFilter) list.push({ key: "section", label: `Section: ${sectionFilter}` });
    if (globalFilter) list.push({ key: "q", label: `Search: ${globalFilter}` });
    return list;
  }, [typeFilter, sectionFilter, globalFilter]);

  const clearFilter = (key: string) => {
    if (key === "type") setTypeFilter("");
    if (key === "section") setSectionFilter("");
    if (key === "q") setGlobalFilter("");
  };

  function handleTableKeyDown(e: React.KeyboardEvent) {
    if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.key)) return;
    e.preventDefault();
    const rows = table.getRowModel().rows;
    if (rows.length === 0) return;
    const colCount = VISIBLE_COLUMN_KEYS.length;
    const rowCount = rows.length;
    const current = focusedCell ?? { row: 0, col: 0 };
    let { row, col } = current;
    if (e.key === "ArrowDown") row = Math.min(row + 1, rowCount - 1);
    else if (e.key === "ArrowUp") row = Math.max(row - 1, 0);
    else if (e.key === "ArrowRight") col = Math.min(col + 1, colCount - 1);
    else if (e.key === "ArrowLeft") col = Math.max(col - 1, 0);
    setFocusedCell({ row, col });
  }

  const totalRows = filtered.length;

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2 mb-3 p-2 bg-surface rounded-lg border border-border-default">
        <div className="relative">
          <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          <input
            type="text"
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Search notes, types..."
            aria-label="Search occurrences"
            className="h-8 pl-8 pr-3 text-[12.5px] rounded-md border border-border-default bg-white focus:border-ces-red focus:outline-none w-64 max-[760px]:w-full"
          />
        </div>
        <div className="inline-flex items-center h-8 rounded-md border border-border-default bg-white text-[12px] hover:border-text-muted focus-within:border-ces-red">
          <span className="px-2 text-text-muted">Type</span>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            aria-label="Filter by type"
            className="bg-transparent pr-2 py-1 text-[12px] font-medium text-text-primary focus:outline-none cursor-pointer"
          >
            <option value="">All types</option>
            {ALL_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        <div className="inline-flex items-center h-8 rounded-md border border-border-default bg-white text-[12px] hover:border-text-muted focus-within:border-ces-red">
          <span className="px-2 text-text-muted">Section</span>
          <select
            value={sectionFilter}
            onChange={(e) => setSectionFilter(e.target.value)}
            aria-label="Filter by section"
            className="bg-transparent pr-2 py-1 text-[12px] font-medium text-text-primary focus:outline-none cursor-pointer"
          >
            <option value="">All sections</option>
            {ALL_SECTIONS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="inline-flex items-center h-8 rounded-md border border-border-default bg-white text-[12px] hover:border-text-muted focus-within:border-ces-red">
          <span className="px-2 text-text-muted">Status</span>
          <select
            aria-label="Filter by status"
            className="bg-transparent pr-2 py-1 text-[12px] font-medium text-text-primary focus:outline-none cursor-pointer"
          >
            <option value="">All rows</option>
          </select>
        </div>
        <div className="ml-auto text-[12px] text-text-muted">
          <span className="text-text-primary font-semibold">{filtered.length}</span> of {occurrences.length} rows
        </div>
      </div>

      {activeFilters.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {activeFilters.map((f) => (
            <span
              key={f.key}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-border-default bg-white text-[11.5px]"
            >
              {f.label}
              <button
                onClick={() => clearFilter(f.key)}
                aria-label={`Remove ${f.label} filter`}
                className="leading-none text-text-muted hover:text-text-primary cursor-pointer"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="overflow-auto max-h-[600px] border border-border-default rounded-lg bg-white">
        <table
          role="grid"
          aria-rowcount={isLoading ? -1 : totalRows}
          className="w-full text-[12.5px] border-collapse"
        >
          <thead>
            <tr className="text-[10.5px] uppercase tracking-wider font-semibold text-text-muted border-b border-border-default">
              <th className="py-2 px-3 text-left font-semibold w-[88px]">Incident Date</th>
              <th className="py-2 px-3 text-left font-semibold w-[130px]">Type</th>
              <th className="py-2 px-3 text-left font-semibold w-[90px]">Section</th>
              <th className="py-2 px-3 text-right font-semibold w-[88px]">MMD</th>
              <th className="py-2 px-3 text-right font-semibold w-[72px]">Page</th>
              <th className="py-2 px-3 text-left font-semibold">Notes</th>
            </tr>
          </thead>
          <tbody ref={tbodyRef} onKeyDown={handleTableKeyDown}>
            {isLoading &&
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={`sk-${i}`} className="animate-pulse border-b border-border-default">
                  {Array.from({ length: VISIBLE_COLUMN_KEYS.length }).map((_, j) => (
                    <td key={j} className="py-2 px-3">
                      <div className={cn("h-4 bg-gray-200 rounded", j < 4 ? "w-3/4" : "w-1/2")} />
                    </td>
                  ))}
                </tr>
              ))}

            {!isLoading &&
              table.getRowModel().rows.map((row, rowIndex) => (
                <tr
                  key={row.id}
                  className="border-b border-border-default hover:bg-slate-50 transition-colors"
                  style={{ height: "40px" }}
                >
                  {row.getVisibleCells().map((cell, colIndex) => {
                    if (!VISIBLE_COLUMN_KEYS.includes(cell.column.id)) return null;
                    const isFocused =
                      focusedCell?.row === rowIndex && focusedCell?.col === colIndex;
                    const isNumeric = cell.column.id === "mmd" || cell.column.id === "page_number";
                    const isDate = cell.column.id === "date";
                    return (
                      <td
                        key={cell.id}
                        role="gridcell"
                        tabIndex={isFocused ? 0 : rowIndex === 0 && colIndex === 0 && !focusedCell ? 0 : -1}
                        data-cell-rc={`${rowIndex}-${colIndex}`}
                        onFocus={() => setFocusedCell({ row: rowIndex, col: colIndex })}
                        className={cn(
                          "py-2 px-3 text-[12.5px] text-text-primary focus:outline-none focus:ring-2 focus:ring-inset focus:ring-ces-red/40",
                          isNumeric && "text-right font-mono tabular-nums text-[12px] text-text-primary",
                          isDate && "font-mono text-[12px] text-text-primary"
                        )}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    );
                  })}
                </tr>
              ))}

            {!isLoading && filtered.length === 0 && (
              <tr>
                <td colSpan={VISIBLE_COLUMN_KEYS.length} className="px-4 py-2">
                  <EmptyState
                    icon={
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={1.5}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <circle cx="12" cy="12" r="10" />
                        <line x1="8" y1="12" x2="16" y2="12" />
                      </svg>
                    }
                    title="No occurrences found for this DDR"
                    description="Occurrences will appear here once the DDR has been fully processed."
                  />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex items-center gap-3 text-[11.5px] text-text-muted">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-[var(--edit-indicator)]" /> manually corrected
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-1 rounded-sm bg-ces-red" /> failed extraction
        </span>
        <span className="ml-auto">Click any cell to edit · Esc cancels · Enter confirms</span>
      </div>
    </div>
  );
}
