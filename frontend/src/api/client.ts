export function resolveApiBaseUrl(value: string | undefined): string {
  return (value ?? "").replace(/\/$/, "");
}

export const apiBaseUrl = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);

export interface DependencyStatus {
  status: "ok" | "degraded" | "unavailable" | "not_configured";
  detail: string | null;
}

export interface Readiness {
  status: "healthy" | "degraded" | "unavailable";
  dependencies: Record<string, DependencyStatus>;
}

export interface Health {
  status: "ok";
  service: string;
  version: string;
}

export interface Version {
  application: string;
  environment: string;
  git_sha: string;
  algorithm: string;
  threshold_config: string;
  routing_data: string;
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Status service returned HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export const statusApi = {
  health: () => get<Health>("/api/v1/health"),
  readiness: () => get<Readiness>("/api/v1/health/ready"),
  version: () => get<Version>("/api/v1/version"),
};
