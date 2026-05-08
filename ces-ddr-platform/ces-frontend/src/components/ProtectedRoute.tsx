import { Navigate, Outlet, useLocation } from "react-router";

import AppShell from "@/components/AppShell";
import { authToken } from "@/lib/auth";

export default function ProtectedRoute() {
  const location = useLocation();

  if (!authToken.isAuthenticated()) {
    return <Navigate replace state={{ from: location }} to="/login" />;
  }

  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}
