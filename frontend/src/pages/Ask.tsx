import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { MessageSquareCode } from "lucide-react";
import { api } from "../services/api";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { NeedsConnection, NeedsRepository, useRepoId } from "../components/Guards";
import { PageHeader } from "../components/PageHeader";
import { ApiError, type AskResponse, type TopK } from "../types";

export function AskPage() {
  const repoId = useRepoId();
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState<TopK>(8);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResponse | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!repoId) return;
    setLoading(true);
    setError(null);
    try {
      const payload = await api.ask(repoId, query.trim(), topK);
      setResult(payload);
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.message : "Ask request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <NeedsConnection>
      <NeedsRepository>
        <PageHeader
          title="Ask Codebase"
          description="Answers are produced only from retrieved chunks. Citations that cannot be validated against the index are dropped."
        />
        <form onSubmit={onSubmit} className="mb-6 space-y-3 rounded-lg border border-slate-200 bg-white p-4">
          <textarea
            required
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={4}
            placeholder="Ask about architecture, a function, or how a flow works"
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
          />
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm text-slate-600">
              top_k
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value) as TopK)}
                className="ml-2 rounded-md border border-slate-200 px-2 py-1"
              >
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={8}>8</option>
                <option value={12}>12</option>
              </select>
            </label>
            <button type="submit" disabled={loading} className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
              {loading ? "Retrieving…" : "Ask"}
            </button>
          </div>
        </form>
        {error ? <ErrorState message={error} /> : null}
        {loading ? <LoadingState label="Running hybrid retrieval and grounding…" /> : null}
        {!loading && !result ? (
          <EmptyState
            icon={MessageSquareCode}
            title="No question yet"
            description="Submit a question to retrieve indexed evidence. If evidence is insufficient, the backend returns a fixed refusal instead of inventing an answer."
          />
        ) : null}
        {result ? (
          <div className="space-y-4">
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">Answer</h2>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-800">{result.answer}</p>
              <p className="mt-3 text-xs text-slate-500">
                Confidence {result.insufficient_evidence ? "0" : result.confidence} · {result.grounded ? "grounded" : "not grounded"}
              </p>
            </section>
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">How It Works</h2>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {result.how_it_works.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">Execution Flow</h2>
              <ol className="mt-2 space-y-2 text-sm">
                {result.execution_flow.map((step) => (
                  <li key={step.step} className="rounded border border-slate-200 px-3 py-2">
                    <span className="font-medium text-slate-900">{step.step}</span>
                    <span className="block text-slate-600">{step.detail}</span>
                  </li>
                ))}
              </ol>
            </section>
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">Key Evidence</h2>
              {result.evidence.length === 0 ? (
                <p className="mt-2 text-sm text-slate-500">No validated citations.</p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {result.evidence.map((item) => (
                    <li key={`${item.file}-${item.start_line}-${item.end_line}`} className="rounded border border-slate-200 p-3 text-sm">
                      <div className="font-medium text-slate-900">
                        {item.file} {item.symbol ? `· ${item.symbol}` : ""}
                      </div>
                      <div className="text-slate-500">
                        lines {item.start_line}–{item.end_line}
                        {item.language ? ` · ${item.language}` : ""}
                      </div>
                      {item.snippet ? <pre className="mt-2 overflow-auto font-mono text-xs text-slate-700">{item.snippet}</pre> : null}
                      {repoId ? (
                        <Link
                          className="mt-2 inline-block text-xs font-medium text-accent"
                          to={`/repositories/${repoId}/explorer?path=${encodeURIComponent(item.file)}`}
                        >
                          Open source
                        </Link>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">Related Files</h2>
              {result.related_files.length === 0 ? (
                <p className="mt-2 text-sm text-slate-500">None.</p>
              ) : (
                <ul className="mt-2 space-y-1 text-sm">
                  {result.related_files.map((file) => (
                    <li key={file}>
                      {repoId ? (
                        <Link className="text-accent hover:underline" to={`/repositories/${repoId}/explorer?path=${encodeURIComponent(file)}`}>
                          {file}
                        </Link>
                      ) : (
                        file
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold text-slate-900">Confidence</h2>
              <p className="mt-2 text-sm text-slate-700">
                {result.insufficient_evidence
                  ? "Insufficient retrieved evidence; no confidence is assigned."
                  : `Model confidence ${result.confidence} after citation validation.`}
              </p>
            </section>
          </div>
        ) : null}
      </NeedsRepository>
    </NeedsConnection>
  );
}
