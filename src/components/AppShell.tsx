import { Link, NavLink, useNavigate } from "react-router";

import { authToken } from "@/lib/auth";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { path: "/", label: "Dashboard" },
  { path: "/history", label: "History" },
  { path: "/query", label: "Query" },
  { path: "/monitor", label: "Monitor" },
  { path: "/settings/keywords", label: "Settings" },
];

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
      <header className="sticky top-0 z-50 border-b border-border-default bg-white/82 backdrop-blur-[12px]">
        <div className="flex items-center gap-4 w-full mx-0 px-6 min-h-[72px] max-[760px]:px-4 max-[760px]:min-h-[52px]">
          <div className="flex items-center gap-1 flex-1">
            <Link to="/" className="flex items-center gap-2.5 no-underline shrink-0" aria-label="CES Home">
              <img
                src="/logo.png"
                alt=""
                className="w-auto h-7 block shrink-0"
                width={120}
                height={28}
                loading="eager"
              />
            </Link>

            <nav className="flex items-center gap-0.5 max-[760px]:hidden" aria-label="Main">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === "/"}
                  className={({ isActive }) =>
                    cn(
                      "inline-flex items-center min-h-9 px-3.5 rounded-md text-[13px] font-semibold text-text-muted no-underline tracking-wide transition-colors duration-150",
                      "hover:text-text-primary hover:bg-black/[0.04]",
                      isActive && "text-white bg-ces-red hover:text-white hover:bg-ces-red-dark",
                      "max-[860px]:px-2.5 max-[860px]:text-xs"
                    )
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-2 shrink-0 ml-auto">
            <button
              type="button"
              className="flex items-center justify-center gap-1.5 min-h-8 px-3 border border-border-default rounded-md bg-white text-text-muted text-xs font-semibold cursor-pointer transition-colors duration-200 hover:text-error-text hover:bg-error-bg hover:border-[#FECACA]"
              onClick={handleLogout}
              aria-label="Sign out"
              title="Sign out"
            >
              <LogoutIcon className="w-4 h-4" />
              <span className="text-xs font-semibold max-[860px]:hidden">Sign out</span>
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 px-8 pt-7 pb-10 bg-surface max-[760px]:px-5 max-[760px]:pt-5 max-[760px]:pb-8">
        {children}
      </main>
    </div>
  );
}
