import { useState, type ChangeEvent } from "react";

import { apiClient, type DDRUploadResponse } from "@/lib/api";

type DDRUploadPanelProps = {
  onUploaded?: (result: DDRUploadResponse, file: File) => void;
};

export default function DDRUploadPanel({ onUploaded }: DDRUploadPanelProps) {
  const [uploadState, setUploadState] = useState<"idle" | "uploading" | "error">("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [fileName, setFileName] = useState<string | null>(null);

  function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setFileName(file.name);
    setUploadState("uploading");
    setUploadProgress(5);
    void apiClient
      .uploadDDR(file, setUploadProgress)
      .then((created) => {
        setUploadProgress(100);
        onUploaded?.(created, file);
      })
      .catch(() => {
        setUploadState("error");
        setUploadProgress(0);
      });
  }

  return (
    <section className="grid p-5 border border-border-default rounded-lg bg-white" aria-label="DDR upload">
      {uploadState === "uploading" ? (
        <div className="grid gap-3.5 min-h-[180px] content-center">
          <strong>{fileName ? `Uploading ${fileName}` : "Uploading DDR PDF"}</strong>
          <progress className="w-full h-3 accent-ces-red" value={uploadProgress} max={100} aria-label="Upload progress" />
        </div>
      ) : (
        <label className="group relative grid min-h-[220px] place-items-center border-[1.5px] border-dashed border-border-input rounded-xl bg-surface text-text-secondary font-bold cursor-pointer transition-all duration-[350ms] overflow-hidden hover:border-ces-red hover:border-solid hover:shadow-[0_0_0_3px_rgba(196,18,48,0.08),0_12px_40px_rgba(196,18,48,0.10)] hover:-translate-y-0.5 before:absolute before:top-3.5 before:left-3.5 before:w-[18px] before:h-[18px] before:border-t-2 before:border-l-2 before:border-ces-red/[0.35] before:rounded-tl-md before:pointer-events-none before:transition-all before:duration-[350ms] after:absolute after:bottom-3.5 after:right-3.5 after:w-[18px] after:h-[18px] after:border-b-2 after:border-r-2 after:border-ces-red/[0.35] after:rounded-br-md after:pointer-events-none after:transition-all after:duration-[350ms] hover:before:w-7 hover:before:h-7 hover:before:border-ces-red hover:after:w-7 hover:after:h-7 hover:after:border-ces-red" style={{ background: "radial-gradient(ellipse 120% 80% at 50% 100%, rgba(196,18,48,0.07) 0%, transparent 55%), radial-gradient(ellipse 60% 40% at 50% 0%, rgba(196,18,48,0.03) 0%, transparent 50%), #F9FAFB" }}>
          <span className="grid place-items-center gap-2.5 z-[1]">
            <svg className="w-10 h-10 text-ces-red opacity-70 transition-all duration-300 group-hover:opacity-100 group-hover:-translate-y-0.5 group-hover:scale-105" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <strong className="inline-flex items-center justify-center gap-2 min-h-10 px-5 rounded-lg bg-ces-red text-white text-sm tracking-wide transition-all duration-250 group-hover:bg-ces-red-dark group-hover:shadow-[0_4px_16px_rgba(196,18,48,0.35)] group-hover:-translate-y-0.5">Upload DDR PDF</strong>
            <span className="text-text-muted text-xs font-medium tracking-wide transition-colors duration-300 group-hover:text-text-secondary">Drop file here or click to browse</span>
          </span>
          <input type="file" accept="application/pdf" aria-label="Upload DDR PDF" onChange={handleUpload} className="absolute w-px h-px opacity-0" />
        </label>
      )}

      {uploadState === "error" ? <p className="m-0 px-3 py-2.5 rounded-lg text-error-text bg-error-bg text-[13px] font-semibold">Upload failed</p> : null}
    </section>
  );
}
