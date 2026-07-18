export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export interface DatasetMetadata {
  is_tabular?: boolean;
  row_count?: number;
  column_count?: number;
  column_names?: string[];
  dtypes?: Record<string, string>;
  missing_values?: Record<string, number>;
  total_missing_values?: number;
  duplicate_rows?: number;
  numeric_columns?: string[];
  categorical_columns?: string[];
  date_columns?: string[];
  text_words?: number;
  note?: string;
}

export interface Dataset {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  created_at: string;
  metadata?: DatasetMetadata;
}

export interface ChartRef {
  id: string;
  name: string;
  url: string;
}

export interface Step {
  id: string;
  index: number;
  goal: string;
  method: string;
  status: "pending" | "running" | "retrying" | "completed" | "failed";
  attempts: number;
  error?: string | null;
  result?: Record<string, unknown> | null;
  charts: ChartRef[];
}

export interface KeyFinding {
  finding: string;
  supporting_numbers: string;
}

export interface Insights {
  title?: string;
  executive_summary?: string;
  key_findings?: KeyFinding[];
  recommendations?: string[];
  limitations?: string[];
}

export interface Review {
  assessment?: string;
  gaps?: string[];
  limitations?: string[];
}

export interface Run {
  id: string;
  dataset_id: string;
  dataset_filename?: string | null;
  prompt: string;
  status:
    | "pending"
    | "planning"
    | "running"
    | "reviewing"
    | "reporting"
    | "completed"
    | "failed";
  error?: string | null;
  created_at: string;
  completed_at?: string | null;
  plan?: { steps: { goal: string; method: string }[] } | null;
  steps?: Step[];
  charts?: ChartRef[];
  reports?: string[];
  insights?: Insights | null;
  review?: Review | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), init);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body.detail) detail = String(body.detail);
    } catch {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function uploadDataset(file: File): Promise<Dataset> {
  const form = new FormData();
  form.append("file", file);
  return request<Dataset>("/api/datasets", { method: "POST", body: form });
}

export function listDatasets(): Promise<Dataset[]> {
  return request<Dataset[]>("/api/datasets");
}

export function getDataset(id: string): Promise<Dataset> {
  return request<Dataset>(`/api/datasets/${id}`);
}

export function createAnalysis(datasetId: string, prompt: string): Promise<Run> {
  return request<Run>("/api/analyses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_id: datasetId, prompt }),
  });
}

export function listAnalyses(): Promise<Run[]> {
  return request<Run[]>("/api/analyses");
}

export function getAnalysis(id: string): Promise<Run> {
  return request<Run>(`/api/analyses/${id}`);
}

export function reportUrl(runId: string, format: string): string {
  return apiUrl(`/api/analyses/${runId}/report?format=${format}`);
}

const TERMINAL: Run["status"][] = ["completed", "failed"];

/**
 * Live run updates: SSE first, transparent fallback to polling.
 * Returns a cleanup function.
 */
export function subscribeToRun(
  runId: string,
  onUpdate: (run: Run) => void,
): () => void {
  let stopped = false;
  let pollTimer: ReturnType<typeof setInterval> | null = null;

  const startPolling = () => {
    if (stopped || pollTimer) return;
    pollTimer = setInterval(async () => {
      try {
        const run = await getAnalysis(runId);
        onUpdate(run);
        if (TERMINAL.includes(run.status)) cleanup();
      } catch {
        /* transient — keep polling */
      }
    }, 1500);
  };

  const source = new EventSource(apiUrl(`/api/analyses/${runId}/events`));
  source.onmessage = (event) => {
    try {
      const run = JSON.parse(event.data) as Run;
      if (!run.id) return;
      onUpdate(run);
      if (TERMINAL.includes(run.status)) cleanup();
    } catch {
      /* ignore malformed frame */
    }
  };
  source.onerror = () => {
    source.close();
    startPolling();
  };

  const cleanup = () => {
    stopped = true;
    source.close();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
  };
  return cleanup;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
