import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { DashboardPage } from "./pages/Dashboard";
import { RepositoriesPage } from "./pages/Repositories";
import { RepositoryDetailPage } from "./pages/RepositoryDetail";
import { AskPage } from "./pages/Ask";
import { ExplorerPage } from "./pages/Explorer";
import { ArchitecturePage } from "./pages/Architecture";
import { SearchPage } from "./pages/Search";
import { InsightsPage } from "./pages/Insights";
import { IndexDetailsPage } from "./pages/IndexDetails";
import { SettingsPage } from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/repositories" element={<RepositoriesPage />} />
        <Route path="/repositories/:id" element={<RepositoryDetailPage />} />
        <Route path="/repositories/:id/ask" element={<AskPage />} />
        <Route path="/repositories/:id/explorer" element={<ExplorerPage />} />
        <Route path="/repositories/:id/architecture" element={<ArchitecturePage />} />
        <Route path="/repositories/:id/search" element={<SearchPage />} />
        <Route path="/repositories/:id/insights" element={<InsightsPage />} />
        <Route path="/repositories/:id/index" element={<IndexDetailsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
