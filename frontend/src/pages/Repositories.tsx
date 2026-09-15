import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { GitBranch } from "lucide-react";
import { api } from "../services/api";
import { useApp } from "../context/AppContext";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { NeedsConnection } from "../components/Guards";
import { PageHeader, formatTime } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import { ApiError, type AnalysisMode, type TopK } from "../types";

export function RepositoriesPage() {
  const { repositories, reposLoading, reposError, refreshRepositories, selectRepository } = useApp();
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [branch, setBranch] = useState("");
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("standard");
  const [topK, setTopK] = useState<TopK>(8);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      const created = await api.createRepository({
        url: url.trim(),
        github_token: token.trim() || undefined,
        branch: branch.trim() || undefined,
        analysis_mode: analysisMode,
        top_k: topK,
      });
      setToken("");
      setUrl("");
      setBranch("");
      selectRepository(created.id);
      await refreshRepositories();
      navigate(`/repositories/${created.id}`);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not add repository");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <NeedsConnection>
      <PageHeader
        title="Repositories"
        description="Index a GitHub repository. Public repositories work without a token. Tokens are sent to the backend only and are never stored in the browser."
      />
      <form onSubmit={onSubmit} className="mb-8 grid gap-4 rounded-lg border border-slate-200 bg-white p-4 lg:grid-cols-2">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">GitHub URL</span>
          <input
            required
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repo"
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">GitHub token (optional)</span>
          <input
            type="password"
            autoComplete="off"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Required only for private repositories"
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Branch</span>
          <input
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            placeholder="Default branch if empty"
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-700">Analysis mode</span>
            <select
              value={analysisMode}
              onChange={(e) => setAnalysisMode(e.target.value as AnalysisMode)}
              className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="quick">quick</option>
              <option value="standard">standard</option>
              <option value="deep">deep</option>
            </select>
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-slate-700">top_k</span>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value) as TopK)}
              className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
            >
              <option value={3}>3</option>
              <option value={5}>5</option>
              <option value={8}>8</option>
              <option value={12}>12</option>
            </select>
          </label>
        </div>
        {formError ? <div className="lg:col-span-2"><ErrorState message={formError} /></div> : null}
        <div className="lg:col-span-2">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {submitting ? "Adding…" : "Add and index"}
          </button>
        </div>
      </form>
      {reposLoading ? <LoadingState label="Loading repositories…" /> : null}
      {reposError ? <ErrorState message={reposError} onRetry={() => void refreshRepositories()} /> : null}
      {!reposLoading && repositories.length === 0 ? (
        <EmptyState
          icon={GitBranch}
          title="No repositories yet"
          description="Paste a GitHub URL above. Indexing runs on the backend and writes to persistent ChromaDB."
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">Repository</th>
                <th className="px-4 py-2 font-medium">Branch</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Last indexed</th>
                <th className="px-4 py-2 font-medium">Files</th>
              </tr>
            </thead>
            <tbody>
              {repositories.map((repo) => (
                <tr key={repo.id} className="border-t border-slate-200">
                  <td className="px-4 py-3">
                    <Link
                      to={`/repositories/${repo.id}`}
                      onClick={() => selectRepository(repo.id)}
                      className="font-medium text-accent hover:underline"
                    >
                      {repo.full_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{repo.branch}</td>
                  <td className="px-4 py-3"><StatusBadge status={repo.status} /></td>
                  <td className="px-4 py-3 text-slate-600">{formatTime(repo.last_indexed)}</td>
                  <td className="px-4 py-3">{repo.stats?.files ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </NeedsConnection>
  );
}
