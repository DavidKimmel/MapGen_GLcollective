import type { GeoResult, Theme, JobStatus } from "../types";

const BASE = "/api";

export async function geocode(q: string): Promise<GeoResult[]> {
  const res = await fetch(`${BASE}/geocode?q=${encodeURIComponent(q)}`);
  return res.json();
}

export async function fetchThemes(): Promise<Theme[]> {
  const res = await fetch(`${BASE}/themes`);
  return res.json();
}

export async function submitGenerate(body: Record<string, unknown>): Promise<string> {
  const res = await fetch(`${BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return data.job_id;
}


export async function pollStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE}/status/${jobId}`);
  return res.json();
}

export function downloadUrl(jobId: string): string {
  return `${BASE}/download/${jobId}`;
}

export async function exportGelato(
  jobId: string,
  sizes?: string[],
  bgColor?: string,
): Promise<{ results: Array<{ size: string; path: string }> }> {
  const res = await fetch(`${BASE}/gelato-export/${jobId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sizes: sizes ?? null, bg_color: bgColor ?? "#F5F2ED" }),
  });
  const data = await res.json();
  if (!res.ok || data.error) {
    throw new Error(data.error || `Export failed (${res.status})`);
  }
  return data;
}
