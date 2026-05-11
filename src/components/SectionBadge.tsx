export const SECTION_COLOURS = {
  Surface: { bg: "bg-emerald-600", text: "text-white", border: "border-emerald-700" },
  "Int.": { bg: "bg-sky-600", text: "text-white", border: "border-sky-700" },
  Main: { bg: "bg-indigo-600", text: "text-white", border: "border-indigo-700" },
} as const;

export function SectionBadge({ section }: { section: string | null | undefined }) {
  if (!section) return null;
  const colors =
    SECTION_COLOURS[section as keyof typeof SECTION_COLOURS] ?? {
      bg: "bg-gray-500",
      text: "text-white",
      border: "border-gray-600",
    };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${colors.bg} ${colors.text} ${colors.border}`}
      aria-label={section}
    >
      {section}
    </span>
  );
}
