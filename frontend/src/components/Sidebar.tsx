import { NavLink, useLocation, useParams } from "react-router-dom";
import type { ReactNode } from "react";
import {
  BookOpen,
  Building2,
  FolderTree,
  GitBranch,
  LayoutDashboard,
  LineChart,
  MessageSquareCode,
  Search,
  Settings,
  Database,
} from "lucide-react";
import { useApp } from "../context/AppContext";

const itemClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 rounded-md px-2.5 py-2 text-sm ${
    isActive ? "bg-accent-50 text-accent-700 font-medium" : "text-slate-600 hover:bg-slate-100"
  }`;

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { selectedId, repositories } = useApp();
  const params = useParams();
  const location = useLocation();
  const repoId = params.id || selectedId || repositories[0]?.id;
  const repoPath = repoId ? `/repositories/${repoId}` : "/repositories";
  const askPath = repoId ? `${repoPath}/ask` : "/repositories";
  const explorerPath = repoId ? `${repoPath}/explorer` : "/repositories";
  const architecturePath = repoId ? `${repoPath}/architecture` : "/repositories";
  const searchPath = repoId ? `${repoPath}/search` : "/repositories";
  const insightsPath = repoId ? `${repoPath}/insights` : "/repositories";
  const indexPath = repoId ? `${repoPath}/index` : "/repositories";

  const askActive = location.pathname.endsWith("/ask") || location.pathname === "/ask";

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-slate-200 px-4 py-4">
        <p className="text-sm font-semibold text-slate-900">Codebase RAG</p>
        <p className="mt-0.5 text-xs text-slate-500">Grounded code intelligence</p>
      </div>
      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-4 scrollbar-thin">
        <Section title="Workspace">
          <NavLink to="/dashboard" className={itemClass} onClick={onNavigate}>
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </NavLink>
          <NavLink to="/repositories" className={itemClass} onClick={onNavigate}>
            <GitBranch className="h-4 w-4" />
            Repositories
          </NavLink>
          <NavLink
            to={askPath}
            onClick={onNavigate}
            className={() => itemClass({ isActive: askActive })}
          >
            <MessageSquareCode className="h-4 w-4" />
            Ask Codebase
          </NavLink>
        </Section>
        <Section title="Analysis">
          <NavLink to={explorerPath} className={itemClass} onClick={onNavigate}>
            <FolderTree className="h-4 w-4" />
            Explorer
          </NavLink>
          <NavLink to={architecturePath} className={itemClass} onClick={onNavigate}>
            <Building2 className="h-4 w-4" />
            Architecture
          </NavLink>
          <NavLink to={searchPath} className={itemClass} onClick={onNavigate}>
            <Search className="h-4 w-4" />
            Code Search
          </NavLink>
          <NavLink to={insightsPath} className={itemClass} onClick={onNavigate}>
            <LineChart className="h-4 w-4" />
            Insights
          </NavLink>
        </Section>
        <Section title="System">
          <NavLink to={indexPath} className={itemClass} onClick={onNavigate}>
            <Database className="h-4 w-4" />
            Index Details
          </NavLink>
          <NavLink to="/settings" className={itemClass} onClick={onNavigate}>
            <Settings className="h-4 w-4" />
            Settings
          </NavLink>
        </Section>
      </nav>
      {repoId ? (
        <div className="border-t border-slate-200 px-4 py-3 text-xs text-slate-500">
          <div className="flex items-center gap-1.5">
            <BookOpen className="h-3.5 w-3.5" />
            <span className="truncate">{repositories.find((r) => r.id === repoId)?.full_name || "Repository selected"}</span>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <p className="mb-1 px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{title}</p>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}
