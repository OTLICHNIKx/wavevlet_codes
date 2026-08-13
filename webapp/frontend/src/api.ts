import type { Experiment, ResearchConfig } from "./types";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail || response.statusText);
  }
  return response.json();
}

export const api = {
  experiments: () => request<Experiment[]>("/api/experiments"),
  experiment: (id: string) => request<Experiment>(`/api/experiments/${id}`),
  presets: () => request<{
    codes: Array<{
      id: string;
      name: string;
      config: ResearchConfig["codes"][number];
    }>;
    experiments: Array<{ id: string; name: string; config: ResearchConfig }>;
    user: Array<{ id: string; name: string; config: ResearchConfig }>;
  }>("/api/presets"),
  validate: (config: ResearchConfig) => request<{ valid: boolean; errors: string[]; warnings: string[]; report: Record<string, number> }>("/api/configs/validate", { method: "POST", body: JSON.stringify(config) }),
  create: (name: string, description: string, config: ResearchConfig) => request<Experiment>("/api/experiments", { method: "POST", body: JSON.stringify({ name, description, config }) }),
  cancel: (id: string) => request<{ cancelled: boolean }>(`/api/experiments/${id}/cancel`, { method: "POST" }),
  logs: (id: string) => request<{ lines: string[] }>(`/api/experiments/${id}/logs`),
  resultSchema: (id: string) => request<{ columns: string[]; numeric_metrics: string[]; codes: string[]; decoders: string[] }>(`/api/experiments/${id}/results/schema`),
  resultData: (id: string) => request<{ columns: string[]; rows: Record<string, unknown>[]; total: number }>(`/api/experiments/${id}/results/data?limit=5000`),
  plot: (payload: unknown) => request<{ series: Array<{ name: string; x: number[]; y: number[] }> }>("/api/plots/preview", { method: "POST", body: JSON.stringify(payload) }),
  importCsv: async (file: File, name: string, description: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("name", name);
    form.append("description", description);
    const response = await fetch("/api/experiments/import/csv", { method: "POST", body: form });
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: response.statusText }));
      const detail = body.detail;
      const errors = detail && typeof detail === "object" && Array.isArray(detail.errors)
        ? detail.errors as string[]
        : [typeof detail === "string" ? detail : response.statusText];
      throw new ImportCsvError(errors);
    }
    return response.json() as Promise<Experiment>;
  }
};

export class ImportCsvError extends Error {
  errors: string[];
  constructor(errors: string[]) {
    super(errors.join("; "));
    this.errors = errors;
  }
}
