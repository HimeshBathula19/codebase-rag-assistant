const STORAGE_KEY = "cra.backendUrl";
const SELECTED_REPO_KEY = "cra.selectedRepositoryId";
export const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

export function getBackendUrl(): string {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored && stored.trim()) {
    return stored.trim().replace(/\/$/, "");
  }
  const fromEnv = import.meta.env.VITE_API_URL;
  if (fromEnv && fromEnv.trim()) {
    return fromEnv.trim().replace(/\/$/, "");
  }
  return DEFAULT_BACKEND_URL;
}

export function setBackendUrl(url: string): void {
  const cleaned = url.trim().replace(/\/$/, "");
  window.localStorage.setItem(STORAGE_KEY, cleaned || DEFAULT_BACKEND_URL);
}

export function getSelectedRepositoryId(): string | null {
  return window.sessionStorage.getItem(SELECTED_REPO_KEY);
}

export function setSelectedRepositoryId(id: string | null): void {
  if (!id) {
    window.sessionStorage.removeItem(SELECTED_REPO_KEY);
    return;
  }
  window.sessionStorage.setItem(SELECTED_REPO_KEY, id);
}
