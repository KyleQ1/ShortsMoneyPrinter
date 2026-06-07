import type { PreflightStatus, RemixRequest, RunPlan, StyleOption } from "./types";

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

export function getPreflight(): Promise<PreflightStatus> {
  return requestJson<PreflightStatus>("/api/preflight");
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
