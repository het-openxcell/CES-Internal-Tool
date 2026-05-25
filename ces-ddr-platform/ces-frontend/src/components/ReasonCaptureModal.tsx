import { useEffect, useMemo, useRef, useState } from "react";

const MODAL_WIDTH = 320;
const MODAL_HEIGHT = 180;
const VIEWPORT_GAP = 12;

type ReasonCaptureModalProps = {
  fieldLabel: string;
  originalValue: string;
  correctedValue: string;
  anchorRect: DOMRect;
  anchorElement?: HTMLElement | null;
  onSubmit: (reason: string) => void | Promise<void>;
  onCancel: () => void;
};

export function ReasonCaptureModal({
  fieldLabel,
  originalValue,
  correctedValue,
  anchorRect,
  anchorElement,
  onSubmit,
  onCancel,
}: ReasonCaptureModalProps) {
  const [reason, setReason] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [currentRect, setCurrentRect] = useState(anchorRect);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const titleId = "reason-capture-title";

  useEffect(() => {
    const updateAnchor = () => setCurrentRect(anchorElement?.getBoundingClientRect() ?? anchorRect);
    updateAnchor();
    window.addEventListener("resize", updateAnchor);
    window.addEventListener("scroll", updateAnchor, true);
    return () => {
      window.removeEventListener("resize", updateAnchor);
      window.removeEventListener("scroll", updateAnchor, true);
    };
  }, [anchorElement, anchorRect]);

  const placement = useMemo(() => {
    const belowSpace = window.innerHeight - currentRect.bottom;
    const aboveSpace = currentRect.top;
    const placeBelow = belowSpace >= aboveSpace;
    const left = Math.min(
      Math.max(currentRect.left, VIEWPORT_GAP),
      Math.max(window.innerWidth - MODAL_WIDTH - VIEWPORT_GAP, VIEWPORT_GAP),
    );

    if (placeBelow) {
      return { top: Math.max(VIEWPORT_GAP, Math.min(currentRect.bottom + 6, window.innerHeight - MODAL_HEIGHT - VIEWPORT_GAP)), left };
    }
    return { top: Math.max(currentRect.top - MODAL_HEIGHT - 6, VIEWPORT_GAP), left };
  }, [currentRect]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const submit = async () => {
    const trimmed = reason.trim();
    if (!trimmed || isSaving) return;
    setIsSaving(true);
    try {
      await onSubmit(trimmed);
    } finally {
      setIsSaving(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape" && !isSaving) {
      event.preventDefault();
      onCancel();
      return;
    }

    if (event.key !== "Tab") return;

    const focusable = Array.from(
      containerRef.current?.querySelectorAll<HTMLElement>("input, button:not(:disabled)") ?? [],
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (!first || !last) return;

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <div
      ref={containerRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onKeyDown={handleKeyDown}
      className="fixed z-50 w-[320px] rounded-lg border border-border-default bg-white p-4 shadow-xl"
      style={placement}
    >
      <h2 id={titleId} className="text-sm font-bold text-text-primary">
        Reason for correction
      </h2>
      <div className="mt-2 rounded-md bg-surface px-3 py-2 text-xs font-medium text-text-primary">
        {fieldLabel}: {originalValue || "—"} → {correctedValue || "—"}
      </div>
      <input
        ref={inputRef}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            void submit();
          }
        }}
        placeholder="Why was this changed?"
        aria-label="Why was this changed?"
        className="mt-3 h-10 w-full rounded-md border border-border-default px-3 text-sm text-text-primary focus:border-ces-red focus:outline-none"
      />
      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSaving}
          className="min-h-9 rounded-md px-3 text-sm font-semibold text-text-muted hover:bg-surface disabled:pointer-events-none disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={() => void submit()}
          disabled={!reason.trim() || isSaving}
          className="min-h-9 rounded-md bg-ces-red px-4 text-sm font-semibold text-white hover:bg-ces-red-dark disabled:pointer-events-none disabled:opacity-50"
        >
          {isSaving ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}

export default ReasonCaptureModal;
