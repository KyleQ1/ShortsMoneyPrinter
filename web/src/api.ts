import type { ModelInfo, PreflightStatus, RemixRequest, RunPlan, StyleInput, StyleOption, UploadResult } from "./types";

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = await response.text();
    try {
      const parsed = JSON.parse(message) as { detail?: string };
      message = parsed.detail || message;
    } catch {
      // The plain text response is already useful enough.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export function getStyles(): Promise<StyleOption[]> {
  return requestJson<StyleOption[]>("/api/styles");
}

export function saveStyle(body: StyleInput): Promise<StyleOption> {
  return requestJson<StyleOption>("/api/styles", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function deleteStyle(key: string): Promise<void> {
  await requestJson<{ deleted: string }>(`/api/styles/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });
}

export function resetStyles(): Promise<StyleOption[]> {
  return requestJson<StyleOption[]>("/api/styles/reset", {
    method: "POST",
  });
}

export function resetStyle(key: string): Promise<StyleOption> {
  return requestJson<StyleOption>(`/api/styles/${encodeURIComponent(key)}/reset`, {
    method: "POST",
  });
}

export function uploadFile(kind: "video" | "image" | "audio", file: File): Promise<UploadResult> {
  const body = new FormData();
  body.append("kind", kind);
  body.append("file", file);
  return requestJson<UploadResult>("/api/uploads", {
    method: "POST",
    body,
  });
}

export function getPreflight(): Promise<PreflightStatus> {
  return requestJson<PreflightStatus>("/api/preflight");
}

export function getModels(): Promise<ModelInfo[]> {
  return requestJson<ModelInfo[]>("/api/models");
}

export function listRuns(): Promise<RunPlan[]> {
  return requestJson<RunPlan[]>("/api/runs");
}

export function getRun(runId: string): Promise<RunPlan> {
  return requestJson<RunPlan>(`/api/runs/${runId}`);
}

export function createPlan(body: RemixRequest): Promise<RunPlan> {
  return requestJson<RunPlan>("/api/runs/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function startRun(runId: string, maxCost: number): Promise<{ run_id: string; status: string }> {
  return requestJson(`/api/runs/${runId}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ max_cost: maxCost }),
  });
}
