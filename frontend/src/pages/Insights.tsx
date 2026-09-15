import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { LineChart } from "lucide-react";
import { api } from "../services/api";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { NeedsConnection, NeedsRepository, useRepoId } from "../components/Guards";
import { PageHeader } from "../components/PageHeader";
import { ApiError, type InsightsResponse } from "../types";

export function InsightsPage() {
  const repoId = useRepoId();
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!repoId) return;
    let cancelled = false;
    setLoading(true);
    void api
      .insights(repoId)
      .then((payload) => {
        if (!cancelled) {
          setData(payload);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load insights");
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
        <PageHeader title="Insights" description="Detected from file paths, symbols, and manifests in the indexed repository." />
        {error ? <ErrorState message={error} /> : null}
        {loading ? <LoadingState label="Loading insights…" /> : null}
        {!loading && !data ? (
          <EmptyState icon={LineChart} title="No insights" description="Index a repository to detect entry points, modules, and dependencies." />
        ) : null}
        {data ? (
          <div className="space-y-4">
            <Section title="Entry points">
              {data.entry_points.length === 0 ? (
                <Empty text="None detected." />
              ) : (
                <ul className="space-y-1 text-sm">
                  {data.entry_points.map((item) => (
                    <li key={`${item.file}-${item.reason}`}>
                      <span className="font-medium">{item.file}</span>
                      <span className="text-slate-500"> — {item.reason}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Section>
            <Section title="Major modules">
              {data.major_modules.length === 0 ? (
                <Empty text="None detected." />
              ) : (
                <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {data.major_modules.map((mod) => (
                    <li key={mod.name} className="rounded border border-slate-200 px-3 py-2 text-sm">
                      {mod.name} <span className="text-slate-500">({mod.files} files)</span>
                    </li>
                  ))}
                </ul>
              )}
            </Section>
            <FileList title="Authentication" files={data.authentication} />
            <FileList title="Database" files={data.database} />
            <FileList title="API routes" files={data.api_routes} />
            <FileList title="Services" files={data.services} />
            <FileList title="Configuration" files={data.configuration} />
            <FileList title="Tests" files={data.tests} />
            <Section title="Dependencies">
              {Object.keys(data.dependencies).length === 0 ? (
                <Empty text="No manifests parsed." />
              ) : (
                Object.entries(data.dependencies).map(([ecosystem, pkgs]) => (
                  <div key={ecosystem} className="mb-3">
                    <p className="text-xs font-semibold uppercase text-slate-500">{ecosystem}</p>
                    <p className="mt-1 text-sm text-slate-700">{pkgs.join(", ")}</p>
                  </div>
                ))
              )}
            </Section>
          </div>
        ) : null}
      </NeedsRepository>
    </NeedsConnection>
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

function FileList({ title, files }: { title: string; files: string[] }) {
  return (
    <Section title={title}>
      {files.length === 0 ? <Empty text="None detected." /> : (
        <ul className="space-y-1 text-sm text-slate-700">
          {files.map((file) => (
            <li key={file}>{file}</li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="text-sm text-slate-500">{text}</p>;
}
