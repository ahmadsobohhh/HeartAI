import type { CaseResult, CaseStatus } from "@/types/heartai";
const base = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try { response = await fetch(`${base}${path}`, { cache: "no-store", ...options }); }
  catch (error) {
    if (error instanceof Error && error.name === "AbortError") throw error;
    throw new Error("Cannot reach the local analysis server. Start the backend on port 8000, then retry.");
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail = body && typeof body === "object" && "detail" in body ? body.detail : null;
    throw new Error(typeof detail === "string" ? detail : `Request failed (${response.status}). Please try again.`);
  }
  return response.json() as Promise<T>;
}
export const health = (signal?: AbortSignal) => request<{ demo_available: boolean; max_upload_bytes: number }>("/health", { signal });
export function createCase(file: File) { const body = new FormData(); body.append("file", file); return request<CaseStatus>("/api/cases", { method: "POST", body }); }
export const createDemo = () => request<CaseStatus>("/api/cases/demo", { method: "POST" });
export const getCaseStatus = (id: string, signal?: AbortSignal) => request<CaseStatus>(`/api/cases/${encodeURIComponent(id)}/status`, { signal });
export async function getCase(id: string, signal?: AbortSignal): Promise<CaseResult> {
  const result = await request<CaseResult>(`/api/cases/${encodeURIComponent(id)}`, { signal });
  if (result.status !== "complete" || !Array.isArray(result.structures) || !result.measurements) throw new Error("This case has not produced complete results yet.");
  return result;
}
export const artifactUrl = (id: string, kind: "overlay" | "segmentation" | "measurements") => `${base}/api/cases/${encodeURIComponent(id)}/${kind}`;
export const meshUrl = (id: string, name = "heart", format: "glb" | "stl" = "glb") => `${base}/api/cases/${encodeURIComponent(id)}/meshes/${encodeURIComponent(name)}?format=${format}`;
