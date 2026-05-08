import { cn } from "@/lib/utils";

type EmptyStateProps = {
  icon: React.ReactNode;
  title: string;
  description: string;
  className?: string;
};

export function EmptyState({ icon, title, description, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "grid place-items-center gap-3.5 py-10 px-6 border-[1.5px] border-dashed border-border-input rounded-xl text-center",
        className,
      )}
      style={{ background: "radial-gradient(ellipse 80% 50% at 50% 100%, rgba(196,18,48,0.04) 0%, transparent 60%), #F9FAFB" }}
    >
      <div className="w-12 h-12 text-text-muted opacity-50">{icon}</div>
      <strong className="text-text-secondary text-[15px] font-semibold">{title}</strong>
      <p className="m-0 max-w-[320px] leading-relaxed text-text-muted">{description}</p>
    </div>
  );
}
