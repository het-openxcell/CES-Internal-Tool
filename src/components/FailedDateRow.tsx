export function FailedDateRow({
  date,
  error,
  colSpan,
  onRetry,
  retrying,
}: {
  date: string;
  error: string;
  colSpan: number;
  onRetry?: () => void;
  retrying?: boolean;
}) {
  return (
    <tr
      style={{ background: "#FEF2F2", borderLeft: "4px solid #C41230" }}
      aria-label="Date resolution failed. Action required."
    >
      <td colSpan={colSpan} className="px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="text-[#C41230] font-bold text-xs uppercase tracking-wide shrink-0">Failed</span>
          <span className="font-medium text-sm text-text-primary tabular-nums">{date}</span>
          <span className="text-text-muted text-xs flex-1">{error}</span>
          {onRetry ? (
            <button
              onClick={onRetry}
              disabled={retrying}
              className="inline-flex items-center gap-1.5 shrink-0 px-2.5 py-1 text-xs font-semibold text-[#C41230] border border-[#C41230] rounded-md bg-white hover:bg-[#FEF2F2] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {retrying ? (
                <>
                  <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" strokeDasharray="60" strokeDashoffset="20" />
                  </svg>
                  Retrying…
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <polyline points="23 4 23 10 17 10" />
                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                  </svg>
                  Retry
                </>
              )}
            </button>
          ) : null}
        </div>
      </td>
    </tr>
  );
}
