import { useState } from "react";

import { cn } from "@/lib/utils";

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

export default function CollapsibleSidebar() {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem("ces-sidebar-collapsed") === "true";
    } catch {
      return false;
    }
  });

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem("ces-sidebar-collapsed", String(next));
  };

  return (
    <aside
      className={cn(
        "shrink-0 flex flex-col border-r border-border-default bg-white transition-[width] duration-200 ease-in-out",
        collapsed ? "w-[48px]" : "w-[220px]"
      )}
      aria-label="Sidebar"
    >
      <div className="flex-1" />

      <div className="px-2 py-2 border-t border-border-default">
        <button
          type="button"
          onClick={toggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="flex items-center justify-center w-full py-3 text-text-muted hover:text-text-primary cursor-pointer rounded-md hover:bg-black/[0.04]"
        >
          <ChevronIcon className={cn("w-4 h-4 transition-transform", collapsed ? "rotate-180" : "")} />
        </button>
      </div>
    </aside>
  );
}
