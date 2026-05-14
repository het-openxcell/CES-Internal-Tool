import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { apiClient, type DDRUploadResponse } from "@/lib/api";

const OPERATORS = [
  "ARC Resources",
  "Tourmaline Oil",
  "Crescent Point",
  "Whitecap Resources",
  "Pembina Pipeline",
  "Birchcliff Energy",
];

type DDRUploadModalProps = {
  open: boolean;
  onClose: () => void;
  onUploaded?: (result: DDRUploadResponse, file: File) => void;
};

export default function DDRUploadModal({ open, onClose, onUploaded }: DDRUploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [operator, setOperator] = useState("ARC Resources");
  const [area, setArea] = useState("");
  const [uploadState, setUploadState] = useState<"idle" | "uploading" | "error">("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      setFile(null);
      setDragOver(false);
      setOperator("ARC Resources");
      setArea("");
      setUploadState("idle");
      setUploadProgress(0);
    }
  }, [open]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && open) onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const handleFileSelect = useCallback((selected: File | null) => {
    if (selected && selected.type === "application/pdf") {
      setFile(selected);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    handleFileSelect(dropped);
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files?.[0] ?? null);
  }, [handleFileSelect]);

  function handleStart() {
    if (!file) return;
    setUploadState("uploading");
    setUploadProgress(5);
    void apiClient
      .uploadDDR(file, operator, area, setUploadProgress)
      .then((created) => {
        setUploadProgress(100);
        onUploaded?.(created, file);
      })
      .catch(() => {
        setUploadState("error");
        setUploadProgress(0);
      });
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/40 grid place-items-center"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Upload DDR PDF"
    >
      <div
        ref={modalRef}
        className="bg-white rounded-xl shadow-[0_20px_60px_-12px_rgba(0,0,0,0.25)] w-full max-w-[520px] mx-4 animate-fade-in-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-4 border-b border-border-default flex items-center">
          <div className="text-sm font-semibold text-text-primary">Upload DDR PDF</div>
          <button
            type="button"
            onClick={onClose}
            className="ml-auto text-text-muted hover:text-text-primary p-1 rounded transition-colors"
            aria-label="Close"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="p-5">
          {uploadState === "uploading" ? (
            <div className="grid gap-3.5 min-h-[180px] content-center text-center">
              <strong className="text-sm text-text-primary">Uploading {file?.name}</strong>
              <progress
                className="w-full h-3 accent-ces-red"
                value={uploadProgress}
                max={100}
                aria-label="Upload progress"
              />
            </div>
          ) : (
            <>
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg py-8 px-6 text-center transition-colors cursor-pointer ${
                  dragOver
                    ? "border-ces-red bg-[#FEF2F2]"
                    : "border-border-default bg-surface"
                }`}
                onClick={() => inputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
                }}
              >
                {!file ? (
                  <>
                    <div className="h-12 w-12 mx-auto rounded-lg bg-white border border-border-default grid place-items-center text-ces-red mb-3">
                      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="17 8 12 3 7 8" />
                        <line x1="12" y1="3" x2="12" y2="15" />
                      </svg>
                    </div>
                    <div className="text-[13px] font-semibold text-text-primary">Drop a Pason DDR PDF here</div>
                    <div className="text-[11.5px] text-text-muted mt-1">or click to browse — .pdf, up to 50 MB</div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-4"
                      onClick={(e) => {
                        e.stopPropagation();
                        inputRef.current?.click();
                      }}
                    >
                      Browse files
                    </Button>
                  </>
                ) : (
                  <>
                    <div className="h-10 w-10 mx-auto rounded-md bg-[#FEF2F2] grid place-items-center text-ces-red mb-2">
                      <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                        <line x1="16" y1="13" x2="8" y2="13" />
                        <line x1="16" y1="17" x2="8" y2="17" />
                        <polyline points="10 9 9 9 8 9" />
                      </svg>
                    </div>
                    <div className="text-[13px] font-semibold text-text-primary">{file.name}</div>
                    <div className="text-[11.5px] text-text-muted mt-0.5">
                      {(file.size / (1024 * 1024)).toFixed(1)} MB
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setFile(null);
                      }}
                      className="text-[11.5px] text-ces-red hover:underline mt-2"
                    >
                      Choose a different file
                    </button>
                  </>
                )}
                <input
                  ref={inputRef}
                  type="file"
                  accept="application/pdf"
                  className="sr-only"
                  onChange={handleInputChange}
                />
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10.5px] uppercase tracking-wider font-semibold text-text-muted">Operator</label>
                  <select
                    className="mt-1 w-full h-9 text-[13px] rounded-md border border-border-default bg-white px-2 focus:outline-none focus:border-ces-red"
                    value={operator}
                    onChange={(e) => setOperator(e.target.value)}
                  >
                    {OPERATORS.map((o) => (
                      <option key={o}>{o}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10.5px] uppercase tracking-wider font-semibold text-text-muted">Area (optional)</label>
                  <input
                    className="mt-1 w-full h-9 text-[13px] rounded-md border border-border-default bg-white px-2 focus:outline-none focus:border-ces-red"
                    placeholder="e.g. Montney, Bakken"
                    value={area}
                    onChange={(e) => setArea(e.target.value)}
                  />
                </div>
              </div>
            </>
          )}

          {uploadState === "error" ? (
            <p className="mt-3 px-3 py-2.5 rounded-lg text-error-text bg-error-bg text-[13px] font-semibold">
              Upload failed
            </p>
          ) : null}
        </div>

        <div className="px-5 py-3 border-t border-border-default bg-surface flex items-center justify-end gap-2 rounded-b-xl">
          <Button variant="outline" size="default" onClick={onClose} disabled={uploadState === "uploading"}>
            Cancel
          </Button>
          <Button
            variant="default"
            size="default"
            disabled={!file || uploadState === "uploading"}
            onClick={handleStart}
          >
            <svg className="w-3.5 h-3.5 mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Start processing
          </Button>
        </div>
      </div>
    </div>
  );
}
