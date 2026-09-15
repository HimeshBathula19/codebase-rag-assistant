import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../services/api";
import { getSelectedRepositoryId, setSelectedRepositoryId } from "../services/settings";
import { ApiError, type HealthResponse, type Repository } from "../types";

interface AppState {
  health: HealthResponse | null;
  healthError: string | null;
  healthLoading: boolean;
  repositories: Repository[];
  reposLoading: boolean;
  reposError: string | null;
  selectedId: string | null;
  refreshHealth: () => Promise<boolean>;
  refreshRepositories: () => Promise<Repository[]>;
  selectRepository: (id: string | null) => void;
  connected: boolean;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [reposLoading, setReposLoading] = useState(false);
  const [reposError, setReposError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(getSelectedRepositoryId());

  const refreshHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      const payload = await api.health();
      setHealth(payload);
      setHealthError(null);
      return true;
    } catch (err) {
      setHealth(null);
      setHealthError(err instanceof ApiError ? err.message : "Backend unavailable");
      return false;
    } finally {
      setHealthLoading(false);
    }
  }, []);

  const refreshRepositories = useCallback(async () => {
    setReposLoading(true);
    try {
      const list = await api.listRepositories();
      setRepositories(list);
      setReposError(null);
      const stored = getSelectedRepositoryId();
      if (stored && list.some((repo) => repo.id === stored)) {
        setSelectedId(stored);
      } else if (list.length > 0) {
        const next = list[0].id;
        setSelectedId(next);
        setSelectedRepositoryId(next);
      } else {
        setSelectedId(null);
        setSelectedRepositoryId(null);
      }
      return list;
    } catch (err) {
      setRepositories([]);
      setReposError(err instanceof ApiError ? err.message : "Could not load repositories");
      return [];
    } finally {
      setReposLoading(false);
    }
  }, []);

  const selectRepository = useCallback((id: string | null) => {
    setSelectedId(id);
    setSelectedRepositoryId(id);
  }, []);

  useEffect(() => {
    void (async () => {
      const ok = await refreshHealth();
      if (ok) {
        await refreshRepositories();
      }
    })();
  }, [refreshHealth, refreshRepositories]);

  const value = useMemo(
    () => ({
      health,
      healthError,
      healthLoading,
      repositories,
      reposLoading,
      reposError,
      selectedId,
      refreshHealth,
      refreshRepositories,
      selectRepository,
      connected: Boolean(health),
    }),
    [
      health,
      healthError,
      healthLoading,
      repositories,
      reposLoading,
      reposError,
      selectedId,
      refreshHealth,
      refreshRepositories,
      selectRepository,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error("useApp must be used within AppProvider");
  }
  return ctx;
}
