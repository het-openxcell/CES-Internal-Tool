import type { ComponentType } from "react";

import DashboardPage from "@/pages/DashboardPage";
import HistoryPage from "@/pages/HistoryPage";
import KeywordsPage from "@/pages/KeywordsPage";
import LoginPage from "@/pages/LoginPage";
import MonitorPage from "@/pages/MonitorPage";
import QueryPage from "@/pages/QueryPage";
import ReportDetailPage from "@/pages/ReportDetailPage";

export type AppRoute = {
  path: string;
  protected: boolean;
  Component: ComponentType;
};

export const APP_ROUTES: AppRoute[] = [
  { path: "/login", protected: false, Component: LoginPage },
  { path: "/", protected: true, Component: DashboardPage },
  { path: "/reports/:id", protected: true, Component: ReportDetailPage },
  { path: "/history", protected: true, Component: HistoryPage },
  { path: "/query", protected: true, Component: QueryPage },
  { path: "/monitor", protected: true, Component: MonitorPage },
  { path: "/settings/keywords", protected: true, Component: KeywordsPage },
];

export const REQUIRED_ROUTES = APP_ROUTES.map(({ path, protected: protectedRoute }) => ({
  path,
  protected: protectedRoute,
}));
