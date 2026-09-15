export type AnalysisMode = "quick" | "standard" | "deep";
export type SearchMode = "keyword" | "semantic" | "hybrid";
export type TopK = 3 | 5 | 8 | 12;

export interface HealthResponse {
  status: string;
  service: string;
  embeddings: {
    model: string;
    fake: boolean;
  };
  llm: {
    configured: boolean;
    model: string | null;
    base_url: string | null;
  };
  retrieval: {
    semantic_weight: number;
    keyword_weight: number;
    default_top_k: number;
  };
  chroma_dir: string;
}

export interface RepositoryStats {
  files?: number | null;
  functions?: number | null;
  classes?: number | null;
  methods?: number | null;
  chunks?: number | null;
  embeddings?: number | null;
  dependencies?: number | null;
  internal_edges?: number | null;
  modules?: number | null;
  entry_points?: number | null;
  skipped_files?: number | null;
  files_reprocessed?: number | null;
  files_unchanged?: number | null;
  files_deleted?: number | null;
  commit?: string | null;
  branch?: string | null;
}

export interface Repository {
  id: string;
  name: string;
  owner: string;
  full_name: string;
  url: string;
  branch: string;
  analysis_mode: AnalysisMode | string;
  top_k: number;
  commit_sha: string | null;
  default_branch: string | null;
  status: string;
  health: string;
  last_indexed: string | null;
  created_at: string;
  updated_at: string;
  stats: RepositoryStats;
  languages: Record<string, number>;
  warnings: string[];
  index_error: string | null;
  duration_ms: number | null;
  semantic_weight: number | null;
  keyword_weight: number | null;
  has_github_token: boolean;
}

export interface RepositoryCreatePayload {
  url: string;
  github_token?: string;
  branch?: string;
  analysis_mode: AnalysisMode;
  top_k: TopK;
  semantic_weight?: number;
  keyword_weight?: number;
}

export interface IndexJob {
  repository_id?: string;
  status: string;
  stage: string | null;
  progress: number;
  message: string | null;
  error: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface EvidenceItem {
  file: string;
  symbol: string | null;
  start_line: number;
  end_line: number;
  snippet?: string | null;
  score?: number | null;
  language?: string | null;
  symbol_type?: string | null;
  relevance?: number | null;
}

export interface AskResponse {
  answer: string;
  confidence: number;
  how_it_works: string[];
  execution_flow: Array<{ step: string; detail: string }>;
  evidence: EvidenceItem[];
  related_files: string[];
  grounded: boolean;
  insufficient_evidence: boolean;
}

export interface SearchResponse {
  query: string;
  mode: SearchMode;
  results: EvidenceItem[];
}

export interface FileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  size?: number;
  children?: FileNode[];
}

export interface FileContent {
  path: string;
  language: string;
  content: string;
  size: number;
  line_count: number;
}

export interface ArchitectureNode {
  id: string;
  label: string;
  kind: "file" | "external" | string;
  language?: string | null;
}

export interface ArchitectureEdge {
  source: string;
  target: string;
  kind: string;
}

export interface ArchitectureGraph {
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
  internal_nodes: number;
  external_nodes: number;
}

export interface InsightsResponse {
  entry_points: Array<{ file: string; reason: string; symbol?: string }>;
  major_modules: Array<{ name: string; files: number }>;
  authentication: string[];
  database: string[];
  api_routes: string[];
  services: string[];
  configuration: string[];
  tests: string[];
  dependencies: Record<string, string[]>;
  symbols_sampled?: number;
}

export interface IndexDetails {
  commit: string | null;
  files: number | null;
  functions: number | null;
  classes: number | null;
  methods: number | null;
  chunks: number | null;
  embeddings: number | null;
  dependencies: number | null;
  languages: Record<string, number>;
  skipped_files: Array<{ file: string; reason: string }>;
  warnings: string[];
  duration: number | null;
  retrieval_settings: {
    top_k: number;
    semantic_weight: number;
    keyword_weight: number;
    embedding_model: string;
    supported_top_k: number[];
  };
  job: IndexJob | null;
  status: string;
  health: string;
  last_indexed: string | null;
  branch: string | null;
  repository: string | null;
}

export interface ApiErrorBody {
  error: string;
  code: string;
  details?: Record<string, unknown>;
}

export class ApiError extends Error {
  status: number;
  code: string;
  details?: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody | string) {
    if (typeof body === "string") {
      super(body);
      this.status = status;
      this.code = "http_error";
    } else {
      super(body.error || "Request failed");
      this.status = status;
      this.code = body.code;
      this.details = body.details;
    }
    this.name = "ApiError";
  }
}
