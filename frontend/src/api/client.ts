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

export interface HeatmapProperties {
  hex_id?: string;
  h3_resolution?: number;
  bypass_trip_count?: number;
  eligible_trip_count?: number;
  unique_driver_count?: number;
  average_deviation_distance_m?: number;
  heat_weight: number;
  display_weight: number;
}

export interface HeatmapFeature {
  type: "Feature";
  properties: HeatmapProperties;
  geometry: {
    type: "Polygon";
    coordinates: number[][][];
  };
}

export interface HeatmapResponse {
  type: "FeatureCollection";
  features: HeatmapFeature[];
  total_bypass_trips?: number;
  total_eligible_trips?: number;
}

export interface HeatmapFilters {
  startTime?: string;
  endTime?: string;
  driverId?: string;
  h3Resolution: number;
}

export function heatmapQueryString(filters: HeatmapFilters): string {
  const params = new URLSearchParams();
  if (filters.startTime) params.set("start_time", filters.startTime);
  if (filters.endTime) params.set("end_time", filters.endTime);
  if (filters.driverId) params.set("driver_id", filters.driverId);
  params.set("h3_resolution", String(filters.h3Resolution));
  return params.toString();
}

export interface LineStringGeometry {
  type: "LineString";
  coordinates: number[][];
}

export interface RouteComparisonResponse {
  trip_id: string;
  trip_status: string;
  started_at: string;
  ended_at: string | null;
  planned_route: {
    id: string;
    route_version: number;
    routing_data_version: string;
    route_source: string;
    geometry: LineStringGeometry;
    ordered_edge_ids: string[];
  } | null;
  matched_segments: Array<{
    id: string;
    segment_no: number;
    result_state: string;
    confidence: number;
    geometry: LineStringGeometry;
    ordered_edge_ids: string[];
    gap_before: boolean;
    match_status: string;
    reason_code: string | null;
  }>;
  total_gaps: number;
}

export const statusApi = {
  health: () => get<Health>("/api/v1/health"),
  readiness: () => get<Readiness>("/api/v1/health/ready"),
  version: () => get<Version>("/api/v1/version"),
};

export const heatmapApi = {
  get: (filters: HeatmapFilters) =>
    get<HeatmapResponse>(`/api/v1/heatmap?${heatmapQueryString(filters)}`),
};

export const tripApi = {
  comparison: (tripId: string) =>
    get<RouteComparisonResponse>(
      `/api/v1/trips/${encodeURIComponent(tripId)}/route-comparison`,
    ),
};
