import { useQueries } from "@tanstack/react-query";
import { statusApi, type DependencyStatus } from "../../api/client";

const labels: Record<string, string> = {
  database: "PostgreSQL",
  postgis: "PostGIS",
  redis: "Redis",
  redis_stream: "Redis Streams",
  osrm: "OSRM Routing",
};

function StatePill({ state }: { state: string }) {
  return (
    <span className={`state state--${state}`}>{state.replace("_", " ")}</span>
  );
}

function DependencyCard({
  name,
  dependency,
}: {
  name: string;
  dependency: DependencyStatus;
}) {
  return (
    <article className="dependency-card">
      <div>
        <span
          className={`pulse pulse--${dependency.status}`}
          aria-hidden="true"
        />
        <h3>{labels[name] ?? name}</h3>
      </div>
      <StatePill state={dependency.status} />
      <p>{dependency.detail ?? "Connection check completed successfully."}</p>
    </article>
  );
}

export function SystemStatusPage() {
  const [health, readiness, version] = useQueries({
    queries: [
      { queryKey: ["health"], queryFn: statusApi.health },
      { queryKey: ["readiness"], queryFn: statusApi.readiness },
      { queryKey: ["version"], queryFn: statusApi.version },
    ],
  });
  const loading = health.isLoading || readiness.isLoading || version.isLoading;
  const error = health.error || readiness.error || version.error;
  const overall = readiness.data?.status ?? (error ? "unavailable" : "loading");

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/status" aria-label="Route Observatory home">
          <span className="brand-mark">RO</span>
          <span>ROUTE OBSERVATORY</span>
        </a>
        <span className="environment">
          {version.data?.environment ?? "connecting"}
        </span>
      </header>

      <main>
        <section className="hero">
          <div>
            <p className="eyebrow">SYSTEM TELEMETRY / FOUNDATION 0.1</p>
            <h1>
              Infrastructure
              <br />
              at a glance.
            </h1>
            <p className="intro">
              Live dependency checks for the route deviation analytics platform.
              Routing remains optional until a pinned local graph is installed.
            </p>
          </div>
          <div className={`overall overall--${overall}`}>
            <span className="radar" />
            <div>
              <small>OVERALL STATE</small>
              <strong>{loading ? "CHECKING" : overall.toUpperCase()}</strong>
            </div>
          </div>
        </section>

        {loading && (
          <section className="notice">Running dependency checks…</section>
        )}
        {error && (
          <section className="notice notice--error" role="alert">
            <strong>Status API unavailable.</strong>
            <span>{error.message}</span>
          </section>
        )}

        {!loading && !error && readiness.data && (
          <section className="status-grid" aria-label="Dependency status">
            {Object.entries(readiness.data.dependencies).map(
              ([name, dependency]) => (
                <DependencyCard
                  key={name}
                  name={name}
                  dependency={dependency}
                />
              ),
            )}
          </section>
        )}

        {!loading &&
          !error &&
          readiness.data &&
          Object.keys(readiness.data.dependencies).length === 0 && (
            <section className="notice">
              No dependency checks were reported.
            </section>
          )}

        <section className="lower-grid">
          <article className="map-placeholder">
            <div className="map-grid" />
            <div className="map-copy">
              <p className="eyebrow">ANALYTICS SURFACE</p>
              <h2>Heatmap intentionally offline</h2>
              <p>
                No simulated route or GPS data is shown. The map surface will
                activate when the ingestion-to-GeoJSON vertical slice is
                implemented.
              </p>
            </div>
          </article>
          <article className="versions">
            <p className="eyebrow">VERSION MANIFEST</p>
            <dl>
              <div>
                <dt>Application</dt>
                <dd>{version.data?.application ?? "—"}</dd>
              </div>
              <div>
                <dt>Algorithm</dt>
                <dd>{version.data?.algorithm ?? "—"}</dd>
              </div>
              <div>
                <dt>Thresholds</dt>
                <dd>{version.data?.threshold_config ?? "—"}</dd>
              </div>
              <div>
                <dt>Routing data</dt>
                <dd>{version.data?.routing_data ?? "—"}</dd>
              </div>
              <div>
                <dt>Git SHA</dt>
                <dd>{version.data?.git_sha ?? "—"}</dd>
              </div>
            </dl>
          </article>
        </section>
      </main>
      <footer>
        <span>READ-ONLY OPERATIONS CONSOLE</span>
        <span>Auto-refresh · 30s</span>
      </footer>
    </div>
  );
}
