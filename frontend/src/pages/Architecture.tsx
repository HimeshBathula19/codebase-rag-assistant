import { useEffect, useState } from "react";
import { Building2 } from "lucide-react";
import { api } from "../services/api";
import { ArchitectureCanvas } from "../components/ArchitectureCanvas";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { NeedsConnection, NeedsRepository, useRepoId } from "../components/Guards";
import { PageHeader } from "../components/PageHeader";
import { ApiError, type ArchitectureGraph } from "../types";

export function ArchitecturePage() {
  const repoId = useRepoId();
  const [graph, setGraph] = useState<ArchitectureGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!repoId) return;
    let cancelled = false;
    setLoading(true);
    void api
      .architecture(repoId)
      .then((payload) => {
        if (!cancelled) {
          setGraph(payload);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load architecture");
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
        <PageHeader
          title="Architecture"
          description="Dependency graph built from parsed imports in the indexed repository. Nodes and edges are not invented."
        />
        {error ? <ErrorState message={error} /> : null}
        {loading ? <LoadingState label="Loading architecture graph…" /> : null}
        {!loading && graph && graph.nodes.length === 0 ? (
          <EmptyState icon={Building2} title="No import graph" description="No internal or external imports were parsed from the indexed files." />
        ) : null}
        {graph && graph.nodes.length > 0 ? <ArchitectureCanvas graph={graph} /> : null}
      </NeedsRepository>
    </NeedsConnection>
  );
}
