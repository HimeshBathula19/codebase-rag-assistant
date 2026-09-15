import { useEffect, useState } from "react";
import { Database } from "lucide-react";
import { api } from "../services/api";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { NeedsConnection, NeedsRepository, useRepoId } from "../components/Guards";
import { PageHeader, StatCard, formatTime, formatValue } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import { ApiError, type IndexDetails } from "../types";

export function IndexDetailsPage() {
  const repoId = useRepoId();
  const [data, setData] = useState<IndexDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!repoId) return;
    let cancelled = false;
    setLoading(true);
    void api
      .indexDetails(repoId)
      .then((payload) => {
        if (!cancelled) {
          setData(payload);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load index details");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [repoId]);

  return (
    <NeedsConnection>
      <NeedsRepository>
        <PageHeader title="Index Details" description="Actual index statistics, skipped files, warnings, and retrieval settings from the backend." />
        {error ? <ErrorState message={error} /> : null}
        {loading ? <LoadingState label="Loading index details…" /> : null}
        {!loading && !data ? (
          <EmptyState icon={Database} title="No index" description="Index a repository to see commit, chunk, and embedding counts." />
        ) : null}
        {data ? (
          <>
            <div className="mb-4 flex items-center gap-2">
              <StatusBadge status={data.status} />
              <span className="text-sm text-slate-500">{data.repository}</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard label="Commit" value={data.commit ? data.commit.slice(0, 12) : "—"} />
              <StatCard label="Files" value={formatValue(data.files)} />
              <StatCard label="Functions" value={formatValue(data.functions)} />
              <StatCard label="Classes" value={formatValue(data.classes)} />
              <StatCard label="Methods" value={formatValue(data.methods)} />
              <StatCard label="Chunks" value={formatValue(data.chunks)} />
              <StatCard label="Embeddings" value={formatValue(data.embeddings)} />
              <StatCard label="Dependencies" value={formatValue(data.dependencies)} />
              <StatCard label="Duration" value={data.duration ? `${(data.duration / 1000).toFixed(1)}s` : "—"} />
              <StatCard label="Last indexed" value={formatTime(data.last_indexed)} />
              <StatCard label="Branch" value={data.branch} />
              <StatCard label="Health" value={data.health} />
            </div>
            <section className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold">Languages</h2>
              {Object.keys(data.languages).length === 0 ? (
                <p className="mt-2 text-sm text-slate-500">None.</p>
              ) : (
                <ul className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(data.languages).map(([lang, count]) => (
                    <li key={lang} className="rounded border border-slate-200 px-3 py-2 text-sm">
                      {lang}: {count}
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold">Retrieval settings</h2>
              <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
                <div>top_k: {data.retrieval_settings.top_k}</div>
                <div>semantic weight: {data.retrieval_settings.semantic_weight}</div>
                <div>keyword weight: {data.retrieval_settings.keyword_weight}</div>
                <div>embedding model: {data.retrieval_settings.embedding_model}</div>
                <div>supported top_k: {data.retrieval_settings.supported_top_k.join(", ")}</div>
              </dl>
            </section>
            <section className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold">Skipped files</h2>
              {data.skipped_files.length === 0 ? (
                <p className="mt-2 text-sm text-slate-500">None recorded.</p>
              ) : (
                <ul className="mt-2 max-h-64 space-y-1 overflow-auto text-sm scrollbar-thin">
                  {data.skipped_files.map((item) => (
                    <li key={`${item.file}-${item.reason}`}>
                      {item.file} <span className="text-slate-500">({item.reason})</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold">Warnings</h2>
              {data.warnings.length === 0 ? (
                <p className="mt-2 text-sm text-slate-500">None.</p>
              ) : (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                  {data.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              )}
            </section>
          </>
        ) : null}
      </NeedsRepository>
    </NeedsConnection>
  );
}
