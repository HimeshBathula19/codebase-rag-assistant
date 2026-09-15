import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { GitBranch, Unplug } from "lucide-react";
import { api } from "../services/api";
import { useApp } from "../context/AppContext";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { PageHeader, StatCard, formatTime, formatValue } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import { ApiError, type IndexDetails, type InsightsResponse, type Repository } from "../types";

export function DashboardPage() {
  const { connected, healthLoading, healthError, repositories, reposLoading, selectedId, refreshHealth } = useApp();
  const [repo, setRepo] = useState<Repository | null>(null);
  const [details, setDetails] = useState<IndexDetails | null>(null);
  const [insights, setInsights] = useState<InsightsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const activeId = selectedId || repositories[0]?.id;

  useEffect(() => {
    if (!connected || !activeId) {
      setRepo(null);
      setDetails(null);
      setInsights(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    void (async () => {
      try {
        const current = await api.getRepository(activeId);
        if (cancelled) return;
        setRepo(current);
        if (current.status === "ready") {
          const [indexDetails, insightPayload] = await Promise.all([
            api.indexDetails(activeId),
            api.insights(activeId).catch(() => null),
          ]);
          if (cancelled) return;
          setDetails(indexDetails);
          setInsights(insightPayload);
        } else {
          setDetails(null);
          setInsights(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load repository");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [connected, activeId]);

  if (healthLoading) {
    return <LoadingState label="Connecting to FastAPI backend…" />;
  }

  if (!connected) {
    return (
      <>
        <PageHeader title="Dashboard" description="Indexed repository metrics from the connected FastAPI backend." />
        <EmptyState
          icon={Unplug}
          title="Backend not connected"
          description="The FastAPI backend must be connected before any repository information can be shown. Start the API, then confirm the backend URL in Settings. This page never displays placeholder statistics."
          action={
            <div className="flex justify-center gap-2">
              <button type="button" onClick={() => void refreshHealth()} className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm">
                Retry connection
              </button>
              <Link to="/settings" className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-white">
                Open Settings
              </Link>
            </div>
          }
        />
        {healthError ? <div className="mt-4"><ErrorState message={healthError} onRetry={() => void refreshHealth()} /></div> : null}
      </>
    );
  }

  if (reposLoading || loading) {
    return <LoadingState label="Loading repository information…" />;
  }

  if (!activeId || !repo) {
    return (
      <>
        <PageHeader title="Dashboard" />
        <EmptyState
          icon={GitBranch}
          title="No repository connected"
          description="Add a GitHub repository to index real files, symbols, chunks, and dependencies."
          action={
            <Link to="/repositories" className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-white">
              Add repository
            </Link>
          }
        />
      </>
    );
  }

  const stats = repo.stats || {};
  const languages = Object.entries(repo.languages || {});

  return (
    <>
      <PageHeader
        title="Dashboard"
        description={`Live data for ${repo.full_name}. Values are empty until indexing finishes.`}
        actions={<StatusBadge status={repo.health || repo.status} />}
      />
      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
      {repo.status !== "ready" ? (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          This repository is not ready yet ({repo.status}). Metrics appear only after a successful index.
          {repo.index_error ? ` ${repo.index_error}` : ""}
        </div>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Repository" value={repo.full_name} />
        <StatCard label="Branch" value={repo.branch} />
        <StatCard label="Commit" value={repo.commit_sha ? repo.commit_sha.slice(0, 12) : "—"} />
        <StatCard label="Last indexed" value={formatTime(repo.last_indexed)} />
        <StatCard label="Files" value={formatValue(stats.files)} />
        <StatCard label="Functions" value={formatValue(stats.functions)} />
        <StatCard label="Classes" value={formatValue(stats.classes)} />
        <StatCard label="Chunks" value={formatValue(stats.chunks)} />
        <StatCard label="Dependencies" value={formatValue(stats.dependencies)} />
        <StatCard label="Health" value={repo.health} />
        <StatCard label="Modules" value={formatValue(stats.modules ?? insights?.major_modules.length)} />
        <StatCard label="Entry points" value={formatValue(stats.entry_points ?? insights?.entry_points.length)} />
      </div>
      <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-slate-900">Languages</h2>
        {languages.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No language counts yet.</p>
        ) : (
          <ul className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {languages.map(([lang, count]) => (
              <li key={lang} className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm">
                <span>{lang}</span>
                <span className="font-medium">{count} files</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      {details ? (
        <p className="mt-4 text-xs text-slate-500">
          Index duration {details.duration ? `${(details.duration / 1000).toFixed(1)}s` : "—"} · embeddings {formatValue(details.embeddings)}
        </p>
      ) : null}
    </>
  );
}
