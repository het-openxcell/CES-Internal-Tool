import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Check, MinusCircle, Search } from "lucide-react";
import { useSearchParams } from "react-router";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";

import { ReasonCaptureModal } from "@/components/ReasonCaptureModal";
import { SectionBadge } from "@/components/SectionBadge";
import { TypeBadge } from "@/components/TypeBadge";
import { EmptyState } from "@/components/ui/empty-state";
import { useCorrections } from "@/hooks/useCorrections";
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
const EDITABLE_FIELDS = ["type", "section", "mmd", "density", "notes"] as const;

type EditableField = (typeof EDITABLE_FIELDS)[number];

type EditingCell = {
  rowId: string;
  field: EditableField;
  rowIndex: number;
  colIndex: number;
  originalValue: string;
  anchorRect: DOMRect;
  anchorElement: HTMLElement | null;
};

type PendingCorrection = EditingCell & {
  correctedValue: string;
};

type NotesCorrection = EditingCell & {
  correctedValue: string;
  reason: string;
  isSaving: boolean;
};

function formatIncidentDate(date: string | null) {
  if (!date) return "—";
  if (/^\d{8}$/.test(date)) return `${date.slice(4, 6)}/${date.slice(6)}/${date.slice(0, 4)}`;
  return date;
}

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

function fieldLabel(field: EditableField) {
  if (field === "mmd") return "MMD";
  return field.charAt(0).toUpperCase() + field.slice(1);
}

function NotesCorrectionPanel({
  correction,
  onValueChange,
  onReasonChange,
  onSubmit,
  onCancel,
}: {
  correction: NotesCorrection;
  onValueChange: (value: string) => void;
  onReasonChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
}) {
  const valueRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [anchorRect, setAnchorRect] = useState(correction.anchorRect);
  const titleId = "notes-correction-title";

  useEffect(() => {
    const updateAnchor = () => setAnchorRect(correction.anchorElement?.getBoundingClientRect() ?? correction.anchorRect);
    updateAnchor();
    window.addEventListener("resize", updateAnchor);
    window.addEventListener("scroll", updateAnchor, true);
    return () => {
      window.removeEventListener("resize", updateAnchor);
      window.removeEventListener("scroll", updateAnchor, true);
    };
  }, [correction.anchorElement, correction.anchorRect]);

  const placement = useMemo(() => {
    const width = Math.min(560, window.innerWidth - 24);
    const height = 360;
    const belowSpace = window.innerHeight - anchorRect.bottom;
    const aboveSpace = anchorRect.top;
    const left = Math.min(
      Math.max(anchorRect.left + anchorRect.width / 2 - width / 2, 12),
      Math.max(window.innerWidth - width - 12, 12),
    );
    const top = belowSpace >= aboveSpace
      ? Math.max(12, Math.min(anchorRect.bottom + 8, window.innerHeight - height - 12))
      : Math.max(anchorRect.top - height - 8, 12);
    return { left, top, width };
  }, [anchorRect]);

  useEffect(() => {
    valueRef.current?.focus();
    valueRef.current?.setSelectionRange(correction.correctedValue.length, correction.correctedValue.length);
  }, []);

  const changed = correction.correctedValue.trim() !== correction.originalValue.trim();
  const canSave = changed && Boolean(correction.reason.trim()) && !correction.isSaving;

  return (
    <div
      ref={containerRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onKeyDown={(event) => {
        if (event.key === "Escape" && !correction.isSaving) {
          event.preventDefault();
          onCancel();
        }
        if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
          event.preventDefault();
          if (canSave) onSubmit();
        }
        if (event.key === "Tab") {
          const focusable = Array.from(
            containerRef.current?.querySelectorAll<HTMLElement>("textarea, input, button:not(:disabled)") ?? [],
          );
          const first = focusable[0];
          const last = focusable[focusable.length - 1];
          if (first && last && event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
          } else if (first && last && !event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
          }
        }
      }}
      className="fixed z-50 rounded-xl border border-border-default bg-white p-4 shadow-2xl"
      style={placement}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 id={titleId} className="text-sm font-bold text-text-primary">Edit notes</h2>
          <p className="mt-1 text-xs text-text-muted">Full notes editor. Ctrl+Enter saves, Esc cancels.</p>
        </div>
        <button
          type="button"
          onClick={onCancel}
          disabled={correction.isSaving}
          className="rounded-md px-2 py-1 text-sm font-semibold text-text-muted hover:bg-surface hover:text-text-primary disabled:pointer-events-none disabled:opacity-50"
        >
          Esc
        </button>
      </div>

      <div className="mt-3 grid gap-3">
        <label className="grid gap-1.5">
          <span className="text-[11px] font-bold uppercase tracking-wider text-text-muted">Corrected notes</span>
          <textarea
            ref={valueRef}
            value={correction.correctedValue}
            onChange={(event) => onValueChange(event.target.value)}
            rows={7}
            className="min-h-[168px] w-full resize-y rounded-lg border border-border-default bg-white px-3 py-2.5 text-sm leading-6 text-text-primary focus:border-ces-red focus:outline-none focus:ring-2 focus:ring-ces-red/10"
          />
        </label>

        <label className="grid gap-1.5">
          <span className="text-[11px] font-bold uppercase tracking-wider text-text-muted">Reason for change</span>
          <input
            value={correction.reason}
            onChange={(event) => onReasonChange(event.target.value)}
            placeholder="Why was this changed?"
            className="h-10 rounded-lg border border-border-default px-3 text-sm text-text-primary focus:border-ces-red focus:outline-none focus:ring-2 focus:ring-ces-red/10"
          />
        </label>
      </div>

      <div className="mt-4 flex items-center justify-between gap-3">
        <div className="text-xs text-text-muted">
          {changed ? "Change ready. Add reason to save." : "No change yet."}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={correction.isSaving}
            className="h-9 rounded-md px-3 text-sm font-semibold text-text-muted hover:bg-surface disabled:pointer-events-none disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onSubmit}
            disabled={!canSave}
            className="h-9 rounded-md bg-ces-red px-4 text-sm font-semibold text-white hover:bg-ces-red-dark disabled:pointer-events-none disabled:opacity-50"
          >
            {correction.isSaving ? "Saving…" : "Save correction"}
          </button>
        </div>
      </div>
    </div>
  );
}

function makeColumns(correctedIds: Set<string>): ColumnDef<OccurrenceRow>[] {
  return [
    {
      id: "edited",
      header: "Edited",
      enableSorting: false,
      cell: ({ row }) => (
        <div className="flex justify-center">
          {correctedIds.has(row.original.id) && (
            <span aria-label="Cell manually corrected" className="h-2 w-2 rounded-full bg-edit-indicator" />
          )}
        </div>
      ),
    },
    {
      accessorKey: "date",
      header: "Incident Date",
      enableHiding: true,
      cell: ({ getValue }) => formatIncidentDate(getValue() as string | null),
    },
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
      header: "MMD",
      cell: ({ getValue }) => (getValue() != null ? (getValue() as number).toFixed(1) : "—"),
    },
    {
      accessorKey: "density",
      header: "Density",
      cell: ({ getValue }) => (getValue() != null ? (getValue() as number).toFixed(2) : "—"),
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
}

const VISIBLE_COLUMN_KEYS = ["edited", "date", "well_name", "surface_location", "type", "section", "mmd", "density", "page_number", "notes"];
const COLUMN_LAYOUT: Record<string, string> = {
  edited: "text-center w-[22px] px-2",
  date: "text-left w-[112px]",
  well_name: "text-left w-[140px]",
  type: "text-left w-[150px]",
  section: "text-left w-[110px]",
  mmd: "text-right w-[96px]",
  density: "text-right w-[96px]",
  surface_location: "text-left w-[160px]",
  page_number: "text-right w-[82px]",
  notes: "text-left",
};

export type OccurrenceTableProps = {
  occurrences: OccurrenceRow[];
  isLoading: boolean;
  onCorrectionSaved?: (change: {
    occurrenceId: string;
    field: EditableField;
    originalValue: string;
    correctedValue: string;
    reason: string;
  }) => void;
};

export function OccurrenceTable({ occurrences, isLoading, onCorrectionSaved }: OccurrenceTableProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const { overrides, correctedIds, errors, saveCorrection, clearError } = useCorrections();

  const [sorting, setSorting] = useState<SortingState>([{ id: "date", desc: true }]);
  const [globalFilter, setGlobalFilter] = useState(() => searchParams.get("q") ?? "");
  const [typeFilter, setTypeFilter] = useState(() => searchParams.get("type") ?? "");
  const [sectionFilter, setSectionFilter] = useState(() => searchParams.get("section") ?? "");
  const [focusedCell, setFocusedCell] = useState<{ row: number; col: number } | null>(null);
  const [editingCell, setEditingCell] = useState<EditingCell | null>(null);
  const [editValue, setEditValue] = useState("");
  const [typeQuery, setTypeQuery] = useState("");
  const [pendingCorrection, setPendingCorrection] = useState<PendingCorrection | null>(null);
  const [notesCorrection, setNotesCorrection] = useState<NotesCorrection | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const toastRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tbodyRef = useRef<HTMLTableSectionElement>(null);
  const suppressNextBlurRef = useRef(false);

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
    if (!focusedCell || editingCell || pendingCorrection || notesCorrection) return;
    const cell = tbodyRef.current?.querySelector<HTMLElement>(
      `[data-cell-rc="${focusedCell.row}-${focusedCell.col}"]`,
    );
    cell?.focus();
  }, [focusedCell, editingCell, pendingCorrection, notesCorrection]);

  useEffect(() => {
    return () => {
      if (toastRef.current) clearTimeout(toastRef.current);
    };
  }, []);

  const rowsWithOverrides = useMemo(
    () => occurrences.map((row) => (overrides[row.id] ? { ...row, ...overrides[row.id] } : row)),
    [occurrences, overrides],
  );

  const filtered = useMemo(() => {
    return rowsWithOverrides
      .filter((row) => !typeFilter || row.type === typeFilter)
      .filter((row) => !sectionFilter || row.section === sectionFilter)
      .filter((row) => {
        if (!globalFilter) return true;
        const q = globalFilter.toLowerCase();
        return [row.well_name, row.surface_location, row.type, row.section, row.notes, row.page_number?.toString()].some((v) =>
          v?.toLowerCase().includes(q),
        );
      });
  }, [rowsWithOverrides, typeFilter, sectionFilter, globalFilter]);

  const columns = useMemo(() => makeColumns(correctedIds), [correctedIds]);

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getRowId: (row) => row.id,
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

  const showToast = useCallback((message: string) => {
    setToast(message);
    if (toastRef.current) clearTimeout(toastRef.current);
    toastRef.current = setTimeout(() => setToast(null), 3000);
  }, []);

  const startEdit = (row: OccurrenceRow, field: EditableField, rowIndex: number, colIndex: number, cell: HTMLTableCellElement) => {
    suppressNextBlurRef.current = false;
    clearError(row.id);
    const originalValue = displayValue(row[field]);
    const anchorElement = cell.closest("tr") ?? cell;
    const anchorRect = anchorElement.getBoundingClientRect();
    setFocusedCell({ row: rowIndex, col: colIndex });

    if (field === "notes") {
      setEditingCell(null);
      setNotesCorrection({
        rowId: row.id,
        field,
        rowIndex,
        colIndex,
        originalValue,
        correctedValue: originalValue,
        reason: "",
        isSaving: false,
        anchorRect,
        anchorElement,
      });
      return;
    }

    setEditingCell({
      rowId: row.id,
      field,
      rowIndex,
      colIndex,
      originalValue,
      anchorRect,
      anchorElement,
    });
    setEditValue(originalValue);
    setTypeQuery("");
  };

  const keepEditedRowVisible = useCallback((field: EditableField, correctedValue: string) => {
    if (field === "type" && typeFilter && correctedValue !== typeFilter) setTypeFilter("");
    if (field === "section" && sectionFilter && correctedValue !== sectionFilter) setSectionFilter("");
    if (globalFilter) setGlobalFilter("");
  }, [globalFilter, sectionFilter, typeFilter]);

  const cancelInlineEdit = useCallback(() => {
    suppressNextBlurRef.current = true;
    setEditingCell(null);
  }, []);

  const openReasonModal = useCallback((correctedValue: string) => {
    if (!editingCell) return;
    const nextValue = correctedValue.trim();
    if (nextValue === editingCell.originalValue.trim()) {
      setEditingCell(null);
      return;
    }
    keepEditedRowVisible(editingCell.field, nextValue);
    setPendingCorrection({ ...editingCell, correctedValue: nextValue });
    setEditingCell(null);
  }, [editingCell, keepEditedRowVisible]);

  const confirmTypeEdit = useCallback((value: string) => {
    const candidate = value.trim();
    if (!candidate) {
      openReasonModal(editValue);
      return;
    }
    const approvedType = ALL_TYPES.find((type) => type.toLowerCase() === candidate.toLowerCase());
    if (approvedType) openReasonModal(approvedType);
  }, [editValue, openReasonModal]);

  const confirmInlineEdit = useCallback((value: string) => {
    if (suppressNextBlurRef.current) {
      suppressNextBlurRef.current = false;
      return;
    }
    openReasonModal(value);
  }, [openReasonModal]);

  const cancelPending = useCallback(() => {
    if (pendingCorrection) setFocusedCell({ row: pendingCorrection.rowIndex, col: pendingCorrection.colIndex });
    setPendingCorrection(null);
  }, [pendingCorrection]);

  const submitPending = useCallback(async (reason: string) => {
    if (!pendingCorrection) return;
    const { rowId, field, correctedValue, rowIndex, colIndex } = pendingCorrection;
    try {
      await saveCorrection(rowId, field, correctedValue, reason);
      onCorrectionSaved?.({
        occurrenceId: rowId,
        field,
        originalValue: pendingCorrection.originalValue,
        correctedValue,
        reason,
      });
      setPendingCorrection(null);
      setFocusedCell({ row: rowIndex, col: colIndex });
      showToast("Correction saved — will inform future extractions");
    } catch {
      setPendingCorrection(null);
      setFocusedCell({ row: rowIndex, col: colIndex });
    }
  }, [onCorrectionSaved, pendingCorrection, saveCorrection, showToast]);

  const cancelNotesCorrection = useCallback(() => {
    if (notesCorrection) setFocusedCell({ row: notesCorrection.rowIndex, col: notesCorrection.colIndex });
    setNotesCorrection(null);
  }, [notesCorrection]);

  const submitNotesCorrection = useCallback(async () => {
    if (!notesCorrection) return;
    const { rowId, correctedValue, reason, rowIndex, colIndex } = notesCorrection;
    if (!correctedValue.trim() || !reason.trim() || correctedValue.trim() === notesCorrection.originalValue.trim()) return;

    keepEditedRowVisible("notes", correctedValue);
    setNotesCorrection((current) => current ? { ...current, isSaving: true } : current);
    try {
      await saveCorrection(rowId, "notes", correctedValue, reason);
      onCorrectionSaved?.({
        occurrenceId: rowId,
        field: "notes",
        originalValue: notesCorrection.originalValue,
        correctedValue,
        reason,
      });
      setNotesCorrection(null);
      setFocusedCell({ row: rowIndex, col: colIndex });
      showToast("Correction saved — will inform future extractions");
    } catch {
      setNotesCorrection(null);
      setFocusedCell({ row: rowIndex, col: colIndex });
    }
  }, [keepEditedRowVisible, notesCorrection, onCorrectionSaved, saveCorrection, showToast]);

  function handleTableKeyDown(event: React.KeyboardEvent) {
    if (editingCell || pendingCorrection || notesCorrection) return;
    if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    const rows = table.getRowModel().rows;
    if (rows.length === 0) return;
    const colCount = VISIBLE_COLUMN_KEYS.length;
    const rowCount = rows.length;
    const current = focusedCell ?? { row: 0, col: 0 };
    let { row, col } = current;
    if (event.key === "ArrowDown") row = Math.min(row + 1, rowCount - 1);
    else if (event.key === "ArrowUp") row = Math.max(row - 1, 0);
    else if (event.key === "ArrowRight") col = Math.min(col + 1, colCount - 1);
    else if (event.key === "ArrowLeft") col = Math.max(col - 1, 0);
    setFocusedCell({ row, col });
  }

  const totalRows = filtered.length;

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2 mb-3 p-2 bg-surface rounded-lg border border-border-default">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted pointer-events-none" />
          <input
            type="text"
            value={globalFilter}
            onChange={(event) => setGlobalFilter(event.target.value)}
            placeholder="Search notes, types..."
            aria-label="Search occurrences"
            className="h-8 pl-8 pr-3 text-[12.5px] rounded-md border border-border-default bg-white focus:border-ces-red focus:outline-none w-64 max-[760px]:w-full"
          />
        </div>
        <div className="inline-flex items-center h-8 rounded-md border border-border-default bg-white text-[12px] hover:border-text-muted focus-within:border-ces-red">
          <span className="px-2 text-text-muted">Type</span>
          <select
            value={typeFilter}
            onChange={(event) => setTypeFilter(event.target.value)}
            aria-label="Filter by type"
            className="bg-transparent pr-2 py-1 text-[12px] font-medium text-text-primary focus:outline-none cursor-pointer"
          >
            <option value="">All types</option>
            {ALL_TYPES.map((type) => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </div>
        <div className="inline-flex items-center h-8 rounded-md border border-border-default bg-white text-[12px] hover:border-text-muted focus-within:border-ces-red">
          <span className="px-2 text-text-muted">Section</span>
          <select
            value={sectionFilter}
            onChange={(event) => setSectionFilter(event.target.value)}
            aria-label="Filter by section"
            className="bg-transparent pr-2 py-1 text-[12px] font-medium text-text-primary focus:outline-none cursor-pointer"
          >
            <option value="">All sections</option>
            {ALL_SECTIONS.map((section) => (
              <option key={section} value={section}>{section}</option>
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
          {activeFilters.map((filter) => (
            <span
              key={filter.key}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-border-default bg-white text-[11.5px]"
            >
              {filter.label}
              <button
                type="button"
                onClick={() => clearFilter(filter.key)}
                aria-label={`Remove ${filter.label} filter`}
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
          className="w-full text-[15px] border-collapse"
        >
          <thead className="bg-surface">
            <tr className="text-[13px] uppercase tracking-wider font-bold text-text-muted border-b border-border-default">
              {table.getHeaderGroups()[0].headers
                .filter((header) => VISIBLE_COLUMN_KEYS.includes(header.column.id))
                .map((header) => {
                  const sort = header.column.getIsSorted();
                  const ariaSort = sort === "asc" ? "ascending" : sort === "desc" ? "descending" : "none";
                  return (
                    <th
                      key={header.id}
                      aria-sort={ariaSort}
                      onClick={header.column.getCanSort() ? header.column.getToggleSortingHandler() : undefined}
                      className={cn(
                        "py-3 px-4 font-bold select-none",
                        header.column.getCanSort() && "cursor-pointer",
                        COLUMN_LAYOUT[header.column.id],
                      )}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  );
                })}
            </tr>
          </thead>
          <tbody ref={tbodyRef} onKeyDown={handleTableKeyDown}>
            {isLoading &&
              Array.from({ length: 5 }).map((_, index) => (
                <tr key={`sk-${index}`} className="animate-pulse border-b border-border-default">
                  {Array.from({ length: VISIBLE_COLUMN_KEYS.length }).map((_, cellIndex) => (
                    <td key={cellIndex} className="py-2 px-3">
                      <div className={cn("h-4 bg-gray-200 rounded", cellIndex < 4 ? "w-3/4" : "w-1/2")} />
                    </td>
                  ))}
                </tr>
              ))}

            {!isLoading &&
              table.getRowModel().rows.map((row, rowIndex) => (
                <Fragment key={row.id}>
                <tr
                  className="border-b border-border-default hover:bg-slate-50 transition-colors"
                  style={{ minHeight: "52px" }}
                >
                  {row.getVisibleCells().map((cell, colIndex) => {
                    if (!VISIBLE_COLUMN_KEYS.includes(cell.column.id)) return null;
                    const columnId = cell.column.id;
                    const editableField = EDITABLE_FIELDS.includes(columnId as EditableField) ? columnId as EditableField : null;
                    const isEditing = editingCell?.rowId === row.original.id && editingCell.field === editableField;
                    const isFocused = focusedCell?.row === rowIndex && focusedCell?.col === colIndex;
                    const isNumeric = columnId === "mmd" || columnId === "page_number";
                    const isDate = columnId === "date";

                    return (
                      <td
                        key={cell.id}
                        role="gridcell"
                        tabIndex={isFocused ? 0 : rowIndex === 0 && colIndex === 0 && !focusedCell ? 0 : -1}
                        data-cell-rc={`${rowIndex}-${colIndex}`}
                        onFocus={() => setFocusedCell({ row: rowIndex, col: colIndex })}
                        onMouseDown={(event) => {
                          if (editableField && !isEditing) event.preventDefault();
                        }}
                        onClick={(event) => {
                          if (editableField && !isEditing) startEdit(row.original, editableField, rowIndex, colIndex, event.currentTarget);
                        }}
                        className={cn(
                          "relative py-3 px-4 text-[15px] text-text-primary leading-5 focus:outline-none focus:ring-1 focus:ring-inset focus:ring-ces-red/20",
                          editableField && "cursor-text hover:bg-[#FDF2F4]",
                          isNumeric && "text-right font-mono tabular-nums text-[14.5px] text-text-primary",
                          isDate && "font-mono text-[14.5px] text-text-primary",
                          COLUMN_LAYOUT[columnId]?.includes("text-center") && "text-center",
                        )}
                      >
                        {isEditing && editableField === "type" ? (
                          <div className="relative text-left">
                            <input
                              autoFocus
                              value={typeQuery}
                              onChange={(event) => setTypeQuery(event.target.value)}
                              onKeyDown={(event) => {
                                if (event.key === "Enter") confirmTypeEdit(typeQuery || editValue);
                                if (event.key === "Escape") cancelInlineEdit();
                              }}
                              onBlur={() => {
                                if (suppressNextBlurRef.current) {
                                  suppressNextBlurRef.current = false;
                                  return;
                                }
                                confirmTypeEdit(typeQuery || editValue);
                              }}
                              placeholder={editValue}
                              aria-label="Edit Type"
                              className="h-8 w-full rounded-md border border-border-default px-2 text-sm focus:border-ces-red focus:outline-none"
                            />
                            <div className="absolute left-0 top-9 z-40 max-h-56 w-56 overflow-auto rounded-md border border-border-default bg-white shadow-lg">
                              {ALL_TYPES.filter((type) => type.toLowerCase().includes(typeQuery.toLowerCase())).map((type) => (
                                <button
                                  key={type}
                                  type="button"
                                  onMouseDown={(event) => event.preventDefault()}
                                  onClick={() => openReasonModal(type)}
                                  className="block w-full px-3 py-2 text-left text-sm hover:bg-surface"
                                >
                                  {type}
                                </button>
                              ))}
                            </div>
                          </div>
                        ) : isEditing && editableField ? (
                          <input
                            autoFocus
                            value={editValue}
                            onChange={(event) => setEditValue(event.target.value)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter") confirmInlineEdit(editValue);
                              if (event.key === "Escape") cancelInlineEdit();
                            }}
                            onBlur={() => confirmInlineEdit(editValue)}
                            aria-label={`Edit ${fieldLabel(editableField)}`}
                            className="h-8 w-full rounded-md border border-border-default px-2 text-sm focus:border-ces-red focus:outline-none"
                          />
                        ) : (
                          flexRender(cell.column.columnDef.cell, cell.getContext())
                        )}

                      </td>
                    );
                  })}
                </tr>
                {errors[row.original.id] && (
                  <tr className="border-b border-border-default bg-red-50/70">
                    <td colSpan={VISIBLE_COLUMN_KEYS.length} className="px-4 py-2">
                      <div className="flex items-center gap-2 text-left text-xs font-medium text-red-700">
                        <span>{errors[row.original.id]}</span>
                        <button
                          type="button"
                          onClick={() => clearError(row.original.id)}
                          className="ml-auto text-red-700 hover:text-red-900"
                          aria-label="Dismiss correction error"
                        >
                          ×
                        </button>
                      </div>
                    </td>
                  </tr>
                )}
                </Fragment>
              ))}

            {!isLoading && filtered.length === 0 && (
              <tr>
                <td colSpan={VISIBLE_COLUMN_KEYS.length} className="px-4 py-2">
                  <EmptyState
                    icon={<MinusCircle aria-hidden="true" />}
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
          <span className="h-2 w-2 rounded-full bg-edit-indicator" /> manually corrected
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-1 rounded-sm bg-ces-red" /> failed extraction
        </span>
        <span className="ml-auto">Click any cell to edit · Esc cancels · Enter confirms</span>
      </div>

      {pendingCorrection && (
        <ReasonCaptureModal
          fieldLabel={fieldLabel(pendingCorrection.field)}
          originalValue={pendingCorrection.originalValue}
          correctedValue={pendingCorrection.correctedValue}
          anchorRect={pendingCorrection.anchorRect}
          anchorElement={pendingCorrection.anchorElement}
          onSubmit={submitPending}
          onCancel={cancelPending}
        />
      )}

      {notesCorrection && (
        <NotesCorrectionPanel
          correction={notesCorrection}
          onValueChange={(value) => setNotesCorrection((current) => current ? { ...current, correctedValue: value } : current)}
          onReasonChange={(value) => setNotesCorrection((current) => current ? { ...current, reason: value } : current)}
          onSubmit={() => void submitNotesCorrection()}
          onCancel={cancelNotesCorrection}
        />
      )}

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-lg bg-[#16A34A] px-4 py-3 text-sm font-semibold text-white shadow-lg">
          <Check className="h-4 w-4" aria-hidden="true" />
          {toast}
        </div>
      )}
    </div>
  );
}
