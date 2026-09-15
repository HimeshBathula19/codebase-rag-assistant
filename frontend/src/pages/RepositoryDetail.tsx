import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../services/api";
import { useApp } from "../context/AppContext";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { NeedsConnection } from "../components/Guards";
import { PageHeader, StatCard, formatTime, formatValue } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import { ApiError, type IndexJob, type Repository } from "../types";

export function RepositoryDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { selectRepository, refreshRepositories } = useApp();
  const [repo, setRepo] = useState<Repository | null>(null);
  const [job, setJob] = useState<IndexJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) selectRepository(id);
  }, [id, selectRepository]);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    async function load() {
      try {
        const current = await api.getRepository(id!);
        const status = await api.indexStatus(id!);
        if (cancelled) return;
        setRepo(current);
        setJob(status);
        setError(null);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load repository");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    const timer = window.setInterval(() => {
      void api.indexStatus(id).then(setJob).catch(() => undefined);
      void api.getRepository(id).then(setRepo).catch(() => undefined);
    }, 2500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [id]);

  async function runIndex(kind: "index" | "reindex") {
    if (!id) return;
    try {
      const next = kind === "index" ? await api.indexRepository(id) : await api.reindexRepository(id);
      setJob(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Indexing request failed");
    }
  }

  async function removeRepo() {
    if (!id) return;
    await api.deleteRepository(id);
    await refreshRepositories();
    navigate("/repositories");
  }

  if (loading) return <LoadingState label="Loading repository…" />;

  return (
    <NeedsConnection>
      {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
      {!repo ? null : (
        <>
          <PageHeader
            title={repo.full_name}
            description={repo.url}
            actions={
              <>
                <button type="button" onClick={() => void runIndex("index")} className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm">
                  Index
                </button>
                <button type="button" onClick={() => void runIndex("reindex")} className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm">
                  Reindex
                </button>
                <button type="button" onClick={() => void removeRepo()} className="rounded-md border border-red-200 bg-white px-3 py-2 text-sm text-red-700">
                  Delete
                </button>
              </>
            }
          />
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <StatusBadge status={repo.status} />
            {job ? <span className="text-sm text-slate-600">{job.stage || job.status} · {job.progress}% {job.message ? `· ${job.message}` : ""}</span> : null}
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Branch" value={repo.branch} />
            <StatCard label="Commit" value={repo.commit_sha ? repo.commit_sha.slice(0, 12) : "—"} />
            <StatCard label="Last indexed" value={formatTime(repo.last_indexed)} />
            <StatCard label="Mode / top_k" value={`${repo.analysis_mode} / ${repo.top_k}`} />
            <StatCard label="Files" value={formatValue(repo.stats?.files)} />
            <StatCard label="Chunks" value={formatValue(repo.stats?.chunks)} />
            <StatCard label="Functions" value={formatValue(repo.stats?.functions)} />
            <StatCard label="Classes" value={formatValue(repo.stats?.classes)} />
          </div>
          <div className="mt-6 flex flex-wrap gap-2 text-sm">
            <Link className="rounded-md border border-slate-200 bg-white px-3 py-2" to={`/repositories/${repo.id}/ask`}>Ask</Link>
            <Link className="rounded-md border border-slate-200 bg-white px-3 py-2" to={`/repositories/${repo.id}/explorer`}>Explorer</Link>
            <Link className="rounded-md border border-slate-200 bg-white px-3 py-2" to={`/repositories/${repo.id}/architecture`}>Architecture</Link>
            <Link className="rounded-md border border-slate-200 bg-white px-3 py-2" to={`/repositories/${repo.id}/search`}>Search</Link>
            <Link className="rounded-md border border-slate-200 bg-white px-3 py-2" to={`/repositories/${repo.id}/insights`}>Insights</Link>
            <Link className="rounded-md border border-slate-200 bg-white px-3 py-2" to={`/repositories/${repo.id}/index`}>Index details</Link>
          </div>
        </>
      )}
    </NeedsConnection>
  );
}
