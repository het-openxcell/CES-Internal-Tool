import { Link, useNavigate } from "react-router";

import CollapsibleSidebar from "@/components/CollapsibleSidebar";
import { authToken } from "@/lib/auth";

function LogoutIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
      <polyline points="10 17 15 12 10 7" />
      <line x1="15" y1="12" x2="3" y2="12" />
    </svg>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  function handleLogout() {
    authToken.clear();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex flex-col min-h-screen">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-3 focus:py-1.5 focus:bg-white focus:border focus:border-ces-red focus:rounded focus:text-ces-red focus:text-sm focus:font-semibold"
      >
        Skip to main content
      </a>

      <header className="sticky top-0 z-50 border-b border-border-default bg-white/82 backdrop-blur-[12px]">
        <div className="flex items-center justify-between w-full px-6 min-h-[56px]">
          <Link to="/" aria-label="CES Home">
            <img
              src="/logo.png"
              alt=""
              className="w-auto h-7 block"
              width={120}
              height={28}
              loading="eager"
            />
          </Link>
          <button
            type="button"
            className="flex items-center justify-center gap-1.5 min-h-8 px-3 border border-border-default rounded-md bg-white text-text-muted text-xs font-semibold cursor-pointer transition-colors duration-200 hover:text-error-text hover:bg-error-bg hover:border-[#FECACA]"
            onClick={handleLogout}
            aria-label="Sign out"
            title="Sign out"
          >
            <LogoutIcon className="w-4 h-4" />
            <span className="text-xs font-semibold">Sign out</span>
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <CollapsibleSidebar />
        <main id="main-content" className="flex-1 overflow-auto px-8 pt-7 pb-10 bg-surface max-[760px]:px-5 max-[760px]:pt-5 max-[760px]:pb-8">
          {children}
        </main>
      </div>
    </div>
  );
}
