export function FailedDateRow({ date, error, colSpan }: { date: string; error: string; colSpan: number }) {
  return (
    <tr
      style={{ background: "#FEF2F2", borderLeft: "4px solid #C41230" }}
      aria-label="Date resolution failed. Action required."
    >
      <td colSpan={colSpan} className="px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="text-[#C41230] font-bold text-xs uppercase tracking-wide shrink-0">Failed</span>
          <span className="font-medium text-sm text-text-primary tabular-nums">{date}</span>
          <span className="text-text-muted text-xs">{error}</span>
        </div>
      </td>
    </tr>
  );
}
