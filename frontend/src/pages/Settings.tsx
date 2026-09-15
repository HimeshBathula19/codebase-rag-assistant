import { FormEvent, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../services/api";
import { useApp } from "../context/AppContext";
import { ErrorState } from "../components/ErrorState";
import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import { DEFAULT_BACKEND_URL, getBackendUrl, setBackendUrl } from "../services/settings";
import { ApiError } from "../types";

export function SettingsPage() {
  const { health, healthError, connected, refreshHealth, refreshRepositories, selectedId, repositories } = useApp();
  const [backendUrl, setUrl] = useState(getBackendUrl());
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const selected = repositories.find((r) => r.id === selectedId);

  async function saveBackend(event: FormEvent) {
    event.preventDefault();
    setBackendUrl(backendUrl);
    const ok = await refreshHealth();
    if (ok) {
      await refreshRepositories();
      setError(null);
      setMessage("Backend URL saved. Connection succeeded.");
    } else {
      setMessage(null);
      setError("Saved the URL, but the backend is not reachable.");
    }
  }

  async function deleteSelected() {
    if (!selectedId) return;
    if (!window.confirm("Delete this repository and its index from the backend?")) return;
    try {
      await api.deleteRepository(selectedId);
      await refreshRepositories();
      setDeleteError(null);
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Delete failed");
    }
  }

  return (
    <>
      <PageHeader title="Settings" description="Frontend configuration and connection status. Secrets stay on the server." />
      <div className="space-y-4">
        <Section title="General">
          <p className="text-sm text-slate-600">Light-only developer workspace. Repository analysis always comes from the indexed checkout.</p>
        </Section>
        <Section title="GitHub">
          <p className="text-sm text-slate-600">
            Optional GitHub tokens are submitted only when adding a repository. They are not written to localStorage and are never returned by the API.
          </p>
        </Section>
        <Section title="Retrieval / RAG">
          {health ? (
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              <div>Semantic weight: {health.retrieval.semantic_weight}</div>
              <div>Keyword weight: {health.retrieval.keyword_weight}</div>
              <div>Default top_k: {health.retrieval.default_top_k}</div>
              <div>Supported top_k: 3, 5, 8, 12</div>
            </dl>
          ) : (
            <p className="text-sm text-slate-500">Connect the backend to read retrieval settings.</p>
          )}
        </Section>
        <Section title="Embeddings">
          <p className="text-sm text-slate-700">{health?.embeddings.model || "sentence-transformers/all-MiniLM-L6-v2"}</p>
          {health?.embeddings.fake ? <p className="mt-1 text-xs text-amber-700">Backend is using fake embeddings (test mode).</p> : null}
        </Section>
        <Section title="ChromaDB">
          <p className="text-sm text-slate-700">{health?.chroma_dir || "Configured on the server (CHROMA_DIR)."}</p>
        </Section>
        <Section title="LLM">
          {health ? (
            <p className="text-sm text-slate-700">
              {health.llm.configured
                ? `Configured · ${health.llm.model} · ${health.llm.base_url}`
                : "Not configured. The backend uses extractive grounded answers only. API keys are never shown here."}
            </p>
          ) : (
            <p className="text-sm text-slate-500">Unavailable until the backend responds.</p>
          )}
        </Section>
        <Section title="Indexing">
          <p className="text-sm text-slate-600">
            Analysis modes: quick, standard, deep. Reindex reuses unchanged file hashes and removes deleted files from ChromaDB.
          </p>
        </Section>
        <Section title="Security / Privacy">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
            <li>Backend URL may be stored in localStorage.</li>
            <li>GitHub tokens are not stored in the browser.</li>
            <li>API responses omit encrypted secrets.</li>
          </ul>
        </Section>
        <Section title="Connection Status">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={connected ? "ok" : "error"} />
            <span className="text-sm text-slate-600">{connected ? "FastAPI reachable" : "Not connected"}</span>
          </div>
          {healthError ? <div className="mt-3"><ErrorState message={healthError} onRetry={() => void refreshHealth()} /></div> : null}
          <form onSubmit={saveBackend} className="mt-4 flex flex-col gap-2 sm:flex-row">
            <input
              value={backendUrl}
              onChange={(e) => setUrl(e.target.value)}
              className="flex-1 rounded-md border border-slate-200 px-3 py-2 text-sm"
              placeholder={DEFAULT_BACKEND_URL}
            />
            <button type="submit" className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white">
              Save and test
            </button>
          </form>
          {message ? <p className="mt-2 text-sm text-emerald-700">{message}</p> : null}
          {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
        </Section>
        <Section title="Danger Zone">
          <p className="text-sm text-slate-600">
            Delete the selected repository from the backend, including its ChromaDB chunks and checkout.
          </p>
          <p className="mt-2 text-sm">Selected: {selected?.full_name || "none"}</p>
          {deleteError ? <div className="mt-2"><ErrorState message={deleteError} /></div> : null}
          <button
            type="button"
            disabled={!selectedId}
            onClick={() => void deleteSelected()}
            className="mt-3 rounded-md border border-red-200 px-3 py-2 text-sm text-red-700 disabled:opacity-50"
          >
            Delete selected repository
          </button>
        </Section>
      </div>
    </>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="mb-2 text-sm font-semibold text-slate-900">{title}</h2>
      {children}
    </section>
  );
}
