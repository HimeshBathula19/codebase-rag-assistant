import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { FolderTree } from "lucide-react";
import { api } from "../services/api";
import { CodeViewer } from "../components/CodeViewer";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { FileTree } from "../components/FileTree";
import { LoadingState } from "../components/LoadingState";
import { NeedsConnection, NeedsRepository, useRepoId } from "../components/Guards";
import { PageHeader } from "../components/PageHeader";
import { ApiError, type FileContent, type FileNode } from "../types";

export function ExplorerPage() {
  const repoId = useRepoId();
  const [params, setParams] = useSearchParams();
  const requested = params.get("path");
  const [tree, setTree] = useState<FileNode[]>([]);
  const [file, setFile] = useState<FileContent | null>(null);
  const [loadingTree, setLoadingTree] = useState(true);
  const [loadingFile, setLoadingFile] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!repoId) return;
    let cancelled = false;
    setLoadingTree(true);
    void api
      .listFiles(repoId)
      .then((payload) => {
        if (!cancelled) {
          setTree(payload.tree);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load file tree");
      })
      .finally(() => {
        if (!cancelled) setLoadingTree(false);
      });
    return () => {
      cancelled = true;
    };
  }, [repoId]);

  useEffect(() => {
    if (!repoId || !requested) {
      setFile(null);
      return;
    }
    let cancelled = false;
    setLoadingFile(true);
    void api
      .getFile(repoId, requested)
      .then((payload) => {
        if (!cancelled) setFile(payload);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load file");
      })
      .finally(() => {
        if (!cancelled) setLoadingFile(false);
      });
    return () => {
      cancelled = true;
    };
  }, [repoId, requested]);

  return (
    <NeedsConnection>
      <NeedsRepository>
        <PageHeader title="Explorer" description="File tree from the indexed checkout. Source is fetched from the backend, not generated in the browser." />
        {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}
        {loadingTree ? <LoadingState label="Loading repository tree…" /> : null}
        {!loadingTree && tree.length === 0 ? (
          <EmptyState icon={FolderTree} title="No files" description="Index a repository before browsing source." />
        ) : null}
        {tree.length > 0 ? (
          <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
            <div className="max-h-[70vh] overflow-auto rounded-lg border border-slate-200 bg-white p-3 scrollbar-thin">
              <FileTree
                nodes={tree}
                selected={requested || undefined}
                onSelect={(node) => {
                  if (node.type === "file") {
                    setParams({ path: node.path });
                  }
                }}
              />
            </div>
            <div>
              {loadingFile ? <LoadingState label="Loading source…" /> : null}
              {!requested && !loadingFile ? (
                <EmptyState icon={FolderTree} title="Select a file" description="Click a file in the tree to load its contents with line numbers." />
              ) : null}
              {file ? <CodeViewer path={file.path} content={file.content} /> : null}
            </div>
          </div>
        ) : null}
      </NeedsRepository>
    </NeedsConnection>
  );
}
