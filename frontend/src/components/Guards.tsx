import { useParams } from "react-router-dom";
import type { ReactNode } from "react";
import { useApp } from "../context/AppContext";
import { EmptyState } from "./EmptyState";
import { GitBranch, Unplug } from "lucide-react";
import { Link } from "react-router-dom";

export function useRepoId(): string | undefined {
  const params = useParams();
  const { selectedId } = useApp();
  return params.id || selectedId || undefined;
}

export function NeedsConnection({ children }: { children: ReactNode }) {
  const { connected, healthLoading, healthError } = useApp();
  if (healthLoading) return <p className="text-sm text-slate-500">Checking backend connection…</p>;
  if (!connected) {
    return (
      <EmptyState
        icon={Unplug}
        title="Backend not connected"
        description="The FastAPI backend must be running and reachable. Start it, then set the backend URL in Settings. This dashboard does not display placeholder statistics."
        action={
          <Link to="/settings" className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-white">
            Open Settings
          </Link>
        }
      />
    );
  }
  if (healthError) {
    return (
      <EmptyState
        icon={Unplug}
        title="Backend not connected"
        description={healthError}
        action={
          <Link to="/settings" className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-white">
            Open Settings
          </Link>
        }
      />
    );
  }
  return <>{children}</>;
}

export function NeedsRepository({ children }: { children: ReactNode }) {
  const repoId = useRepoId();
  const { repositories } = useApp();
  if (!repoId) {
    return (
      <EmptyState
        icon={GitBranch}
        title="No repository selected"
        description="Add a GitHub repository first. All analysis views read from an indexed checkout — nothing is fabricated."
        action={
          <Link to="/repositories" className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-white">
            Add repository
          </Link>
        }
      />
    );
  }
  if (!repositories.some((r) => r.id === repoId) && repositories.length > 0) {
    return (
      <EmptyState
        icon={GitBranch}
        title="Repository not found"
        description="This repository is not available on the connected backend."
        action={
          <Link to="/repositories" className="text-sm font-medium text-accent">
            Back to repositories
          </Link>
        }
      />
    );
  }
  return <>{children}</>;
}
