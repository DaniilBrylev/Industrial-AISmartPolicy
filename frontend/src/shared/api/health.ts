import { apiUrl } from "@/shared/api/client";

export type HealthResponse = {
  status: string;
  service: string;
  llm_enabled?: boolean;
};

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(apiUrl("/api/health"));
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return (await res.json()) as HealthResponse;
}
