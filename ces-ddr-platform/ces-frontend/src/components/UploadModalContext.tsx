import { createContext, useContext, useState, type ReactNode } from "react";

const UploadModalContext = createContext<{
  open: boolean;
  setOpen: (v: boolean) => void;
} | null>(null);

export function UploadModalProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <UploadModalContext.Provider value={{ open, setOpen }}>
      {children}
    </UploadModalContext.Provider>
  );
}

export function useUploadModal() {
  const ctx = useContext(UploadModalContext);
  return ctx ?? { open: false, setOpen: () => {} };
}
