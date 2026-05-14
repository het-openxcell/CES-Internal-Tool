import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";

export type ReprocessMode = "full" | "dates" | "occurrences";

type ReprocessModalProps = {
  open: boolean;
  ddrId: string;
  availableDates: string[];
  onClose: () => void;
  onSubmitted?: (mode: ReprocessMode) => void;
  onOccurrencesRegenerated?: () => void;
};

export default function ReprocessModal({ open, ddrId, availableDates, onClose, onSubmitted, onOccurrencesRegenerated }: ReprocessModalProps) {
  const [mode, setMode] = useState<ReprocessMode>("full");
  const [selectedDates, setSelectedDates] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setMode("full");
      setSelectedDates(new Set());
      setSubmitting(false);
      setError(null);
    }
  }, [open]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && open && !submitting) onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose, submitting]);

  const sortedDates = useMemo(() => [...availableDates].sort(), [availableDates]);
  const allSelected = sortedDates.length > 0 && selectedDates.size === sortedDates.length;

  function toggleDate(date: string) {
    setSelectedDates((prev) => {
      const next = new Set(prev);
      if (next.has(date)) next.delete(date);
      else next.add(date);
      return next;
    });
  }

  function toggleAll() {
    setSelectedDates(allSelected ? new Set() : new Set(sortedDates));
  }

  async function handleConfirm() {
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "full") {
        await apiClient.reprocessFull(ddrId);
        onSubmitted?.(mode);
        onClose();
      } else if (mode === "dates") {
        const dates = allSelected ? "all" : Array.from(selectedDates);
        if (!allSelected && dates.length === 0) {
          setError("Select at least one date");
          setSubmitting(false);
          return;
        }
        await apiClient.reprocessDates(ddrId, dates);
        onSubmitted?.(mode);
        onClose();
      } else {
        const result = await apiClient.reprocessOccurrences(ddrId);
        if (result.status !== "success") {
          setError(result.error || "Occurrence regeneration failed");
          setSubmitting(false);
          return;
        }
        onOccurrencesRegenerated?.();
        onSubmitted?.(mode);
        onClose();
      }
    } catch {
      setError(mode === "occurrences" ? "Occurrence regeneration failed" : "Reprocess failed to start");
      setSubmitting(false);
    }
  }

  if (!open) return null;

  function formatDate(d: string) {
    if (d.length === 8) return `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;
    return d;
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 grid place-items-center"
      onClick={() => { if (!submitting) onClose(); }}
      role="dialog"
      aria-label="Reprocess DDR"
    >
      <div
        className="bg-white rounded-xl shadow-[0_20px_60px_-12px_rgba(0,0,0,0.25)] w-full max-w-[520px] mx-4 animate-fade-in-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-4 border-b border-border-default flex items-center">
          <div className="text-sm font-semibold text-text-primary">Reprocess DDR</div>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="ml-auto text-text-muted hover:text-text-primary p-1 rounded transition-colors disabled:opacity-50"
            aria-label="Close"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="p-5 space-y-3">
          <ReprocessOption
            id="full"
            selected={mode === "full"}
            onSelect={() => setMode("full")}
            title="Reprocess from scratch"
            description="Re-split the PDF, re-extract every date, and regenerate the occurrence table. Old data stays visible until the new extraction succeeds per date."
          />
          <ReprocessOption
            id="dates"
            selected={mode === "dates"}
            onSelect={() => setMode("dates")}
            title="Reprocess specific dates"
            description="Re-extract chosen dates only, then regenerate the occurrence table."
          />
          {mode === "dates" && (
            <div className="ml-7 mt-2 border border-border-default rounded-md bg-surface">
              <div className="px-3 py-2 border-b border-border-default flex items-center justify-between">
                <span className="text-[11.5px] font-semibold text-text-secondary">
                  {selectedDates.size} of {sortedDates.length} selected
                </span>
                <button
                  type="button"
                  onClick={toggleAll}
                  className="text-[11.5px] font-semibold text-ces-red hover:underline"
                >
                  {allSelected ? "Clear all" : "Select all"}
                </button>
              </div>
              <div className="max-h-[180px] overflow-auto p-2 grid grid-cols-2 gap-1">
                {sortedDates.length === 0 ? (
                  <div className="text-[12px] text-text-muted col-span-2 px-2 py-3 text-center">No dates available</div>
                ) : (
                  sortedDates.map((d) => (
                    <label
                      key={d}
                      className="flex items-center gap-2 text-[12px] text-text-primary px-2 py-1 rounded hover:bg-white cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedDates.has(d)}
                        onChange={() => toggleDate(d)}
                        className="accent-ces-red"
                      />
                      <span>{formatDate(d)}</span>
                    </label>
                  ))
                )}
              </div>
            </div>
          )}
          <ReprocessOption
            id="occurrences"
            selected={mode === "occurrences"}
            onSelect={() => setMode("occurrences")}
            title="Regenerate occurrence table only"
            description="Keep extracted data as-is. Re-run the LLM to rebuild the occurrence table."
          />

          {error && (
            <div className="text-[12px] text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
          )}
        </div>

        <div className="px-5 py-3 border-t border-border-default flex items-center justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button size="sm" onClick={handleConfirm} disabled={submitting}>
            {submitting ? (mode === "occurrences" ? "Regenerating…" : "Starting…") : "Confirm"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function ReprocessOption({
  id,
  selected,
  onSelect,
  title,
  description,
}: {
  id: string;
  selected: boolean;
  onSelect: () => void;
  title: string;
  description: string;
}) {
  return (
    <label
      htmlFor={`reprocess-${id}`}
      className={`flex items-start gap-2.5 p-3 rounded-md border cursor-pointer transition-colors ${
        selected ? "border-ces-red bg-[#FEF2F2]" : "border-border-default bg-white hover:bg-surface"
      }`}
    >
      <input
        type="radio"
        id={`reprocess-${id}`}
        name="reprocess-mode"
        checked={selected}
        onChange={onSelect}
        className="mt-0.5 accent-ces-red"
      />
      <div className="min-w-0">
        <div className="text-[13px] font-semibold text-text-primary">{title}</div>
        <div className="text-[11.5px] text-text-muted mt-0.5 leading-snug">{description}</div>
      </div>
    </label>
  );
}
