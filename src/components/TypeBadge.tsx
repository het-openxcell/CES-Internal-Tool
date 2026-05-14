export const TYPE_COLOURS: Record<string, { bg: string; text: string }> = {
  "Stuck Pipe": { bg: "bg-red-100", text: "text-red-800" },
  "Lost Circulation": { bg: "bg-orange-100", text: "text-orange-800" },
  "Back Ream": { bg: "bg-amber-100", text: "text-amber-800" },
  Ream: { bg: "bg-yellow-100", text: "text-yellow-800" },
  "Tight Hole": { bg: "bg-lime-100", text: "text-lime-800" },
  Washout: { bg: "bg-green-100", text: "text-green-800" },
  "BHA Failure": { bg: "bg-teal-100", text: "text-teal-800" },
  Vibration: { bg: "bg-cyan-100", text: "text-cyan-800" },
  "Kick / Well Control": { bg: "bg-sky-100", text: "text-sky-800" },
  H2S: { bg: "bg-blue-100", text: "text-blue-800" },
  Deviation: { bg: "bg-indigo-100", text: "text-indigo-800" },
  Fishing: { bg: "bg-violet-100", text: "text-violet-800" },
  "Pack Off": { bg: "bg-purple-100", text: "text-purple-800" },
  "Casing Issue": { bg: "bg-fuchsia-100", text: "text-fuchsia-800" },
  "Cementing Issue": { bg: "bg-pink-100", text: "text-pink-800" },
  "Bit Failure": { bg: "bg-rose-100", text: "text-rose-800" },
};

const FALLBACK = { bg: "bg-gray-100", text: "text-gray-700" };

export function TypeBadge({ type }: { type: string }) {
  const label = type || "Unknown";
  const colors = TYPE_COLOURS[label] ?? FALLBACK;
  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded text-[13px] font-semibold ${colors.bg} ${colors.text}`}
      aria-label={label}
    >
      {label}
    </span>
  );
}
