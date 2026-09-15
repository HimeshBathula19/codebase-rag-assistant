import { FormEvent, useState } from "react";
import { Search } from "lucide-react";
import { api } from "../services/api";
import { CodeViewer } from "../components/CodeViewer";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { NeedsConnection, NeedsRepository, useRepoId } from "../components/Guards";
import { PageHeader } from "../components/PageHeader";
import { ApiError, type EvidenceItem, type FileContent, type SearchMode, type TopK } from "../types";

export function SearchPage() {
  const repoId = useRepoId();
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [topK, setTopK] = useState<TopK>(8);
  const [results, setResults] = useState<EvidenceItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<FileContent | null>(null);
  const [range, setRange] = useState<{ start: number; end: number } | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!repoId) return;
    setLoading(true);
    setError(null);
    setSource(null);
    try {
      const payload = await api.search(repoId, query.trim(), mode, topK);
      setResults(payload.results);
    } catch (err) {
      setResults(null);
      setError(err instanceof ApiError ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  async function openResult(item: EvidenceItem) {
    if (!repoId) return;
    try {
      const file = await api.getFile(repoId, item.file);
      setSource(file);
      setRange({ start: item.start_line, end: item.end_line });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load source");
    }
  }

  return (
    <NeedsConnection>
      <NeedsRepository>
        <PageHeader title="Code Search" description="Keyword, semantic, or hybrid retrieval over indexed chunks for this repository only." />
        <form onSubmit={onSubmit} className="mb-6 flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:flex-row sm:items-end">
          <label className="flex-1 text-sm">
            Query
            <input
              required
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2"
            />
          </label>
          <label className="text-sm">
            Mode
            <select value={mode} onChange={(e) => setMode(e.target.value as SearchMode)} className="mt-1 block rounded-md border border-slate-200 px-3 py-2">
              <option value="hybrid">hybrid</option>
              <option value="semantic">semantic</option>
              <option value="keyword">keyword</option>
            </select>
          </label>
          <label className="text-sm">
            top_k
            <select value={topK} onChange={(e) => setTopK(Number(e.target.value) as TopK)} className="mt-1 block rounded-md border border-slate-200 px-3 py-2">
              <option value={3}>3</option>
              <option value={5}>5</option>
              <option value={8}>8</option>
              <option value={12}>12</option>
            </select>
          </label>
          <button type="submit" className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white">
            Search
          </button>
        </form>
        {error ? <ErrorState message={error} /> : null}
        {loading ? <LoadingState label="Searching indexed chunks…" /> : null}
        {!loading && results && results.length === 0 ? (
          <EmptyState icon={Search} title="No matches" description="Nothing in this repository’s index matched the query." />
        ) : null}
        {!loading && results === null ? (
          <EmptyState icon={Search} title="Search the index" description="Results include file, symbol, language, line range, and relevance from the backend." />
        ) : null}
        <div className="grid gap-4 lg:grid-cols-2">
          <ul className="space-y-2">
            {(results || []).map((item) => (
              <li key={`${item.file}-${item.start_line}-${item.end_line}-${item.symbol}`}>
                <button
                  type="button"
                  onClick={() => void openResult(item)}
                  className="w-full rounded-lg border border-slate-200 bg-white p-3 text-left hover:border-accent"
                >
                  <div className="text-sm font-medium text-slate-900">{item.file}</div>
                  <div className="mt-1 text-xs text-slate-500">
                    {item.symbol || "file"} · {item.language || "unknown"} · lines {item.start_line}–{item.end_line} · relevance {item.relevance ?? item.score ?? "—"}
                  </div>
                </button>
              </li>
            ))}
          </ul>
          {source ? (
            <CodeViewer
              path={source.path}
              content={source.content}
              highlightStart={range?.start}
              highlightEnd={range?.end}
            />
          ) : null}
        </div>
      </NeedsRepository>
    </NeedsConnection>
  );
}
