import {
  ApiError,
  type ArchitectureGraph,
  type AskResponse,
  type FileContent,
  type FileNode,
  type HealthResponse,
  type IndexDetails,
  type IndexJob,
  type InsightsResponse,
  type Repository,
  type RepositoryCreatePayload,
  type SearchMode,
  type SearchResponse,
  type TopK,
} from "../types";
import { getBackendUrl } from "./settings";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = `${getBackendUrl()}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...(init.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(0, {
      error: "Cannot reach the FastAPI backend. Check the backend URL in Settings.",
      code: "network_failure",
    });
  }

  const text = await response.text();
  const payload = text ? safeJson(text) : null;
  if (!response.ok) {
    if (payload && typeof payload === "object" && "error" in payload) {
      throw new ApiError(response.status, payload as { error: string; code: string; details?: Record<string, unknown> });
    }
    throw new ApiError(response.status, text || response.statusText);
  }
  return payload as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export const api = {
  health: () => request<HealthResponse>("/health"),

  listRepositories: () => request<Repository[]>("/repositories"),

  getRepository: (id: string) => request<Repository>(`/repositories/${id}`),

  createRepository: (payload: RepositoryCreatePayload) =>
    request<Repository>("/repositories", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  deleteRepository: (id: string) =>
    request<{ deleted: boolean; id: string }>(`/repositories/${id}`, { method: "DELETE" }),

  indexRepository: (id: string) =>
    request<IndexJob>(`/repositories/${id}/index`, { method: "POST" }),

  reindexRepository: (id: string) =>
    request<IndexJob>(`/repositories/${id}/reindex`, { method: "POST" }),

  indexStatus: (id: string) => request<IndexJob>(`/repositories/${id}/index/status`),

  ask: (id: string, query: string, top_k?: TopK) =>
    request<AskResponse>(`/repositories/${id}/ask`, {
      method: "POST",
      body: JSON.stringify({ query, top_k }),
    }),

  search: (id: string, query: string, mode: SearchMode, top_k?: TopK) =>
    request<SearchResponse>(`/repositories/${id}/search`, {
      method: "POST",
      body: JSON.stringify({ query, mode, top_k }),
    }),

  listFiles: (id: string) => request<{ tree: FileNode[] }>(`/repositories/${id}/files`),

  getFile: (id: string, filePath: string) =>
    request<FileContent>(`/repositories/${id}/files/${encodeURI(filePath)}`),

  architecture: (id: string) => request<ArchitectureGraph>(`/repositories/${id}/architecture`),

  insights: (id: string) => request<InsightsResponse>(`/repositories/${id}/insights`),

  indexDetails: (id: string) => request<IndexDetails>(`/repositories/${id}/index-details`),
};
