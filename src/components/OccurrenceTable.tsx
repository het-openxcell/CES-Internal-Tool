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
import { FailedDateRow } from "@/components/FailedDateRow";
import { EmptyState } from "@/components/ui/empty-state";
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
  { accessorKey: "date", header: "Date", enableHiding: true },
  {
    accessorKey: "well_name",
    header: "Well Name",
    cell: ({ getValue }) => (getValue() as string | null) ?? "—",
  },
  {
    accessorKey: "surface_location",
    header: "Surface Location",
    cell: ({ getValue }) => (getValue() as string | null) ?? "—",
  },
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
    header: "mMD (m)",
    cell: ({ getValue }) => (getValue() != null ? (getValue() as number).toFixed(1) : "—"),
  },
  {
    accessorKey: "density",
    header: "Density",
    cell: ({ getValue }) => (getValue() != null ? (getValue() as number).toFixed(2) : "—"),
  },
  {
    accessorKey: "notes",
    header: "Notes",
    cell: ({ getValue }) => (getValue() as string | null) ?? "—",
  },
];

const VISIBLE_COLUMN_KEYS = ["well_name", "surface_location", "type", "section", "mmd", "density", "notes"];

function SortIcon({ state }: { state: "asc" | "desc" | false }) {
  if (state === "asc") return <span aria-hidden>↑</span>;
  if (state === "desc") return <span aria-hidden>↓</span>;
  return <span className="opacity-30" aria-hidden>⇅</span>;
}

export type OccurrenceTableProps = {
  occurrences: OccurrenceRow[];
  failedDates: { date: string; error: string }[];
  isLoading: boolean;
};

export function OccurrenceTable({ occurrences, failedDates, isLoading }: OccurrenceTableProps) {
  const [searchParams, setSearchParams] = useSearchParams();

  const [sorting, setSorting] = useState<SortingState>([{ id: "date", desc: true }]);
  const [globalFilter, setGlobalFilter] = useState(() => searchParams.get("q") ?? "");
  const [typeFilter, setTypeFilter] = useState(() => searchParams.get("type") ?? "");
  const [sectionFilter, setSectionFilter] = useState(() => searchParams.get("section") ?? "");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tbodyRef = useRef<HTMLTableSectionElement>(null);
  const [focusedCell, setFocusedCell] = useState<{ row: number; col: number } | null>(null);

  // Write local state → URL (debounced, functional update avoids searchParams dep)
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

  // Read URL → local state (handles browser back/forward navigation)
  useEffect(() => {
    setTypeFilter(searchParams.get("type") ?? "");
    setSectionFilter(searchParams.get("section") ?? "");
    setGlobalFilter(searchParams.get("q") ?? "");
  }, [searchParams]);

  // Move DOM focus when keyboard navigation changes active cell
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
        return [row.well_name, row.surface_location, row.type, row.section, row.notes].some((v) =>
          v?.toLowerCase().includes(q),
        );
      });
  }, [occurrences, typeFilter, sectionFilter, globalFilter]);

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting, columnVisibility: { date: false } },
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

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Search occurrences..."
          aria-label="Search occurrences"
          className="min-h-[36px] px-3 py-1.5 border border-border-default rounded-md bg-white text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-ces-red/30 focus:border-ces-red w-[260px] max-[760px]:w-full"
        />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          aria-label="Filter by type"
          className="min-h-[36px] px-3 py-1.5 border border-border-default rounded-md bg-white text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-ces-red/30 focus:border-ces-red"
        >
          <option value="">All Types</option>
          {ALL_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select
          value={sectionFilter}
          onChange={(e) => setSectionFilter(e.target.value)}
          aria-label="Filter by section"
          className="min-h-[36px] px-3 py-1.5 border border-border-default rounded-md bg-white text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-ces-red/30 focus:border-ces-red"
        >
          <option value="">All Sections</option>
          {ALL_SECTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {activeFilters.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {activeFilters.map((f) => (
            <span
              key={f.key}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-gray-100 text-xs font-medium text-text-secondary"
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

      <div className="overflow-auto max-h-[600px] border border-border-default rounded-xl">
        <table
          role="grid"
          aria-rowcount={isLoading ? -1 : filtered.length + failedDates.length}
          className="w-full text-sm border-collapse"
        >
          <thead className="sticky top-0 z-10 bg-white">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b border-border-default">
                {headerGroup.headers
                  .filter((h) => VISIBLE_COLUMN_KEYS.includes(h.column.id))
                  .map((header) => (
                    <th
                      key={header.id}
                      className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-text-muted bg-white cursor-pointer select-none"
                      onClick={header.column.getToggleSortingHandler()}
                      aria-sort={
                        header.column.getIsSorted() === "asc"
                          ? "ascending"
                          : header.column.getIsSorted() === "desc"
                            ? "descending"
                            : "none"
                      }
                    >
                      <span className="inline-flex items-center gap-1">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        <SortIcon state={header.column.getIsSorted()} />
                      </span>
                    </th>
                  ))}
              </tr>
            ))}
          </thead>
          <tbody ref={tbodyRef} onKeyDown={handleTableKeyDown}>
            {isLoading &&
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={`sk-${i}`} className="animate-pulse border-b border-border-default">
                  {Array.from({ length: VISIBLE_COLUMN_KEYS.length }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className={`h-4 bg-gray-200 rounded ${j < 4 ? "w-3/4" : "w-1/2"}`} />
                    </td>
                  ))}
                </tr>
              ))}

            {!isLoading &&
              table.getRowModel().rows.map((row, rowIndex) => (
                <tr
                  key={row.id}
                  className="border-b border-border-default hover:bg-slate-50 transition-colors"
                >
                  {row.getVisibleCells().map((cell, colIndex) => {
                    if (!VISIBLE_COLUMN_KEYS.includes(cell.column.id)) return null;
                    const isFocused =
                      focusedCell?.row === rowIndex && focusedCell?.col === colIndex;
                    return (
                      <td
                        key={cell.id}
                        role="gridcell"
                        tabIndex={isFocused ? 0 : rowIndex === 0 && colIndex === 0 && !focusedCell ? 0 : -1}
                        data-cell-rc={`${rowIndex}-${colIndex}`}
                        onFocus={() => setFocusedCell({ row: rowIndex, col: colIndex })}
                        className="px-4 py-2.5 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-inset focus:ring-ces-red/40"
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    );
                  })}
                </tr>
              ))}

            {!isLoading &&
              failedDates.map((fd) => (
                <FailedDateRow
                  key={`${fd.date}-${fd.error.slice(0, 30)}`}
                  date={fd.date}
                  error={fd.error}
                  colSpan={VISIBLE_COLUMN_KEYS.length}
                />
              ))}

            {!isLoading && filtered.length === 0 && failedDates.length === 0 && (
              <tr>
                <td colSpan={VISIBLE_COLUMN_KEYS.length} className="px-4 py-2">
                  <EmptyState
                    icon={
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
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
    </div>
  );
}
