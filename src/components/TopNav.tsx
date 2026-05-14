import { useState, useRef, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router";

import { useUploadModal } from "@/components/UploadModalContext";
import { cn } from "@/lib/utils";

function ReportsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
      <path d="M14 3v6h6" />
      <path d="M8 13h8M8 17h5" />
    </svg>
  );
}

function QueryIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  );
}

function HistoryIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 12a9 9 0 1 0 3-6.7" />
      <path d="M3 3v6h6" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

function MonitorIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="4" width="18" height="13" rx="2" />
      <path d="M8 21h8M12 17v4" />
      <path d="m7 11 3 2 3-4 4 3" />
    </svg>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  );
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M17 8l-5-5-5 5" />
      <path d="M12 3v12" />
    </svg>
  );
}

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.67 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.67 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.67a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function LogoutIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
      <polyline points="10 17 15 12 10 7" />
      <line x1="15" y1="12" x2="3" y2="12" />
    </svg>
  );
}

const TABS = [
  { key: "reports", label: "Reports", path: "/", Icon: ReportsIcon },
  { key: "query", label: "Query", path: "/query", Icon: QueryIcon },
  { key: "history", label: "History", path: "/history", Icon: HistoryIcon },
  { key: "monitor", label: "Monitor", path: "/monitor", Icon: MonitorIcon },
];

export default function TopNav({ onLogout }: { onLogout: () => void }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { setOpen } = useUploadModal();
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  const activeKey = TABS.find((t) =>
    t.path === "/" ? location.pathname === "/" : location.pathname.startsWith(t.path)
  )?.key ?? "reports";

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  return (
    <header className="h-14 border-b border-border-default bg-white flex items-center px-4 sticky top-0 z-30 shrink-0">
      <div className="flex items-center gap-2.5 pr-5 mr-2 border-r border-border-default h-full">
        <Link to="/" aria-label="CES Home" className="shrink-0">
          <img src="/logo.png" alt="" className="h-7 w-auto block" width={120} height={28} loading="eager" />
        </Link>
      </div>

      <nav className="flex items-center gap-0.5 ml-1" aria-label="Primary">
        {TABS.map((t) => {
          const active = activeKey === t.key;
          return (
            <Link
              key={t.key}
              to={t.path}
              className={cn(
                "relative h-14 px-3.5 flex items-center gap-1.5 text-[13px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ces-red focus-visible:ring-offset-2 rounded-sm",
                active ? "text-ces-red" : "text-text-secondary hover:text-text-primary"
              )}
            >
              <t.Icon className="w-4 h-4" />
              <span className="hidden md:inline">{t.label}</span>
              {active && <span className="absolute bottom-0 left-2 right-2 h-[2px] bg-ces-red rounded-full" />}
            </Link>
          );
        })}
      </nav>

      <div className="ml-auto flex items-center gap-2">
        <div className="relative hidden lg:block">
          <SearchIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted pointer-events-none" />
          <input
            type="text"
            placeholder="Search reports, wells, operators…"
            className="h-9 w-64 xl:w-72 pl-8 pr-3 text-[13px] rounded-md bg-surface border border-border-default focus:bg-white focus:border-text-muted focus:outline-none transition-colors"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                const q = (e.target as HTMLInputElement).value;
                if (q) navigate(`/query?q=${encodeURIComponent(q)}`);
              }
            }}
          />
        </div>

        <button
          type="button"
          onClick={() => setOpen(true)}
          className="inline-flex items-center justify-center gap-1.5 h-9 px-3 rounded-md text-[13px] font-semibold bg-ces-red text-white hover:bg-ces-red-dark transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ces-red focus-visible:ring-offset-2 shrink-0"
        >
          <UploadIcon className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Upload DDR</span>
        </button>

        <div ref={profileRef} className="relative hidden md:block">
          <button
            type="button"
            onClick={() => setProfileOpen((v) => !v)}
            className="flex items-center gap-2 pl-2 ml-1 border-l border-border-default h-9 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ces-red focus-visible:ring-offset-2 rounded-sm"
            aria-haspopup="menu"
            aria-expanded={profileOpen}
          >
            <div className="h-7 w-7 rounded-full bg-ces-red text-white grid place-items-center text-[11px] font-bold">
              RC
            </div>
            <div className="text-[11px] leading-tight pr-1 text-left">
              <div className="font-semibold text-text-primary">Ryan Cordell</div>
              <div className="text-text-muted">Operations</div>
            </div>
          </button>

          {profileOpen && (
            <div
              className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg border border-border-default shadow-[0_8px_24px_-8px_rgba(15,23,42,0.18),0_2px_6px_-2px_rgba(15,23,42,0.08)] py-1 z-50"
              role="menu"
            >
              <Link
                to="/settings/keywords"
                onClick={() => setProfileOpen(false)}
                className="flex items-center gap-2.5 px-3 py-2 text-[13px] text-text-secondary hover:bg-surface hover:text-text-primary transition-colors"
                role="menuitem"
              >
                <SettingsIcon className="w-4 h-4" />
                Settings
              </Link>
              <div className="mx-3 my-1 h-px bg-border-default" />
              <button
                type="button"
                onClick={() => { setProfileOpen(false); onLogout(); }}
                className="flex items-center gap-2.5 px-3 py-2 text-[13px] text-text-secondary hover:text-error-text hover:bg-error-bg transition-colors w-full"
                role="menuitem"
              >
                <LogoutIcon className="w-4 h-4" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
