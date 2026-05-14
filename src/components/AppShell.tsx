import { useNavigate } from "react-router";

import DDRUploadModal from "@/components/DDRUploadModal";
import TopNav from "@/components/TopNav";
import { UploadModalProvider, useUploadModal } from "@/components/UploadModalContext";
import { authToken } from "@/lib/auth";

function AppShellInner({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const { open, setOpen } = useUploadModal();

  function handleLogout() {
    authToken.clear();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-3 focus:py-1.5 focus:bg-white focus:border focus:border-ces-red focus:rounded focus:text-ces-red focus:text-sm focus:font-semibold"
      >
        Skip to main content
      </a>

      <TopNav onLogout={handleLogout} />

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {children}
      </div>

      <DDRUploadModal
        open={open}
        onClose={() => setOpen(false)}
        onUploaded={() => {
          setOpen(false);
          navigate("/monitor");
        }}
      />
    </div>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <UploadModalProvider>
      <AppShellInner>{children}</AppShellInner>
    </UploadModalProvider>
  );
}
