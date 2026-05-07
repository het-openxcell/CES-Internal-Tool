import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import ProtectedRoute from "@/components/ProtectedRoute";
import LoginPage from "@/pages/LoginPage";
import { APP_ROUTES } from "@/routes";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          {APP_ROUTES.filter((route) => route.protected).map(({ path, Component }) => (
            <Route key={path} path={path} element={<Component />} />
          ))}
          <Route path="*" element={<Navigate replace to="/" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
