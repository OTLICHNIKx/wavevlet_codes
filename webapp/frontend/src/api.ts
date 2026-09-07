import type { CustomPreset, Experiment, ExperimentPreview, ResearchConfig } from "./types";

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
    user: CustomPreset[];
  }>("/api/presets"),
  validate: (config: ResearchConfig) => request<{ valid: boolean; errors: string[]; warnings: string[]; report: Record<string, number> }>("/api/configs/validate", { method: "POST", body: JSON.stringify(config) }),
  preview: (config: ResearchConfig) => request<ExperimentPreview>("/api/configs/preview", { method: "POST", body: JSON.stringify(config) }),
  create: (name: string, description: string, config: ResearchConfig) => request<Experiment>("/api/experiments", { method: "POST", body: JSON.stringify({ name, description, config }) }),
  cancel: (id: string) => request<{ cancelled: boolean }>(`/api/experiments/${id}/cancel`, { method: "POST" }),
  deleteExperiment: (id: string) =>
    request<{ deleted: boolean }>(`/api/experiments/${id}`, { method: "DELETE" }),
  logs: (id: string) => request<{ lines: string[] }>(`/api/experiments/${id}/logs`),
  resultSchema: (id: string) => request<{ columns: string[]; numeric_metrics: string[]; codes: string[]; decoders: string[] }>(`/api/experiments/${id}/results/schema`),
  resultData: (id: string) => request<{ columns: string[]; rows: Record<string, unknown>[]; total: number }>(`/api/experiments/${id}/results/data?limit=5000`),
  plot: (payload: unknown) => request<{ series: Array<{ name: string; x: number[]; y: number[] }> }>("/api/plots/preview", { method: "POST", body: JSON.stringify(payload) }),
  importCsv: (file: File, name: string, description: string) =>
    uploadForImport("/api/experiments/import/csv", file, name, description),
  importPackage: (file: File, name: string, description: string) =>
    uploadForImport("/api/experiments/import/package", file, name, description),
  exportExperiment: async (id: string, name: string) => {
    const response = await fetch(`/api/experiments/${id}/export`);
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(body.detail || response.statusText);
    }
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${name || "experiment"}.zip`;
    link.click();
    URL.revokeObjectURL(link.href);
  },
  createPreset: (name: string, description: string, config: ResearchConfig) =>
    request<CustomPreset>("/api/presets", { method: "POST", body: JSON.stringify({ name, description, config }) }),
  updatePreset: (id: string, name: string, description: string, config: ResearchConfig) =>
    request<CustomPreset>(`/api/presets/${id}`, { method: "PUT", body: JSON.stringify({ name, description, config }) }),
  duplicatePreset: (id: string) =>
    request<CustomPreset>(`/api/presets/${id}/duplicate`, { method: "POST" }),
  deletePreset: (id: string) =>
    request<{ deleted: boolean }>(`/api/presets/${id}`, { method: "DELETE" }),
  cloneExperimentPreset: (id: string) =>
    request<CustomPreset>(`/api/experiments/${id}/clone-preset`, { method: "POST" }),
  importPreset: (file: File) => uploadPreset(file),
  exportPreset: async (id: string, name: string) => {
    const response = await fetch(`/api/presets/${id}/export`);
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(typeof body.detail === "string" ? body.detail : response.statusText);
    }
    const blob = await response.blob();
    downloadBlob(blob, `${name || "preset"}.preset.json`);
  },
};

function downloadBlob(blob: Blob, filename: string) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

async function uploadPreset(file: File): Promise<CustomPreset> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/presets/import", { method: "POST", body: form });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    const detail = body.detail;
    const errors = detail && typeof detail === "object" && Array.isArray(detail.errors)
      ? detail.errors as string[]
      : [typeof detail === "string" ? detail : response.statusText];
    throw new ImportCsvError(errors);
  }
  return response.json() as Promise<CustomPreset>;
}

async function uploadForImport(
  path: string,
  file: File,
  name: string,
  description: string,
): Promise<Experiment> {
  const form = new FormData();
  form.append("file", file);
  form.append("name", name);
  form.append("description", description);
  const response = await fetch(path, { method: "POST", body: form });
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

export class ImportCsvError extends Error {
  errors: string[];
  constructor(errors: string[]) {
    super(errors.join("; "));
    this.errors = errors;
  }
}
