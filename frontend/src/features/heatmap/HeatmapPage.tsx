import { useQuery } from "@tanstack/react-query";
import { useCallback, useMemo, useState, type FormEvent } from "react";
import { heatmapApi, tripApi, type HeatmapFilters } from "../../api/client";
import {
  HeatmapMap,
  type HeatmapViewMode,
  type MapHoverInfo,
} from "./HeatmapMap";
import { toH3Cells } from "./heatmap";

const DEFAULT_FILTERS: HeatmapFilters = { h3Resolution: 9 };
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function optionalIsoDate(value: string): string | undefined {
  return value ? new Date(value).toISOString() : undefined;
}

export function HeatmapPage() {
  const [filters, setFilters] = useState<HeatmapFilters>(DEFAULT_FILTERS);
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [driverId, setDriverId] = useState("");
  const [resolution, setResolution] = useState(9);
  const [auditTripInput, setAuditTripInput] = useState("");
  const [auditTripId, setAuditTripId] = useState("");
  const [showPlannedRoute, setShowPlannedRoute] = useState(true);
  const [showActualRoute, setShowActualRoute] = useState(true);

  const query = useQuery({
    queryKey: ["heatmap", filters],
    queryFn: async () => {
      const startedAt = performance.now();
      const response = await heatmapApi.get(filters);
      return { response, responseMs: performance.now() - startedAt };
    },
    // Giu layer cu trong luc refetch de map khong nhap nhay khi doi filter.
    placeholderData: (previousData) => previousData,
    refetchInterval: 30_000,
  });
  const auditQuery = useQuery({
    queryKey: ["route-comparison", auditTripId],
    queryFn: () => tripApi.comparison(auditTripId),
    enabled: UUID_PATTERN.test(auditTripId),
  });
  const cells = useMemo(
    () => toH3Cells(query.data?.response.features ?? []),
    [query.data],
  );
  const [hoverInfo, setHoverInfo] = useState<MapHoverInfo | null>(null);
  const [viewMode, setViewMode] = useState<HeatmapViewMode>("h3-grid");
  const handleHover = useCallback(
    (info: MapHoverInfo | null) => setHoverInfo(info),
    [],
  );
  const handleViewMode = useCallback((mode: HeatmapViewMode) => {
    setViewMode(mode);
    setHoverInfo(null);
  }, []);
  const applyFilters = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFilters({
      startTime: optionalIsoDate(startTime),
      endTime: optionalIsoDate(endTime),
      driverId: driverId.trim() || undefined,
      h3Resolution: resolution,
    });
  };
  const resetFilters = () => {
    setStartTime("");
    setEndTime("");
    setDriverId("");
    setResolution(9);
    setFilters(DEFAULT_FILTERS);
  };
  const loadAudit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuditTripId(auditTripInput.trim());
  };
  const totalVolume = cells.reduce(
    (sum, cell) => sum + cell.bypassTripCount,
    0,
  );
  const resolutions = [...new Set(cells.map((cell) => cell.resolution))].sort();
  const volumes = cells.map((cell) => cell.bypassTripCount);
  const minimumVolume = volumes.length ? Math.min(...volumes) : 0;
  const maximumVolume = volumes.length ? Math.max(...volumes) : 0;

  return (
    <div className="map-page">
      <header className="map-header">
        <a className="brand" href="/heatmap">
          <span className="brand-mark">RO</span>
          <span>ROUTE OBSERVATORY</span>
        </a>
        <nav className="map-nav" aria-label="Điều hướng chính">
          <a className="map-nav__active" href="/heatmap">
            Heatmap
          </a>
          <a href="/status">System status</a>
        </nav>
      </header>

      <main className="map-workspace">
        <aside className="map-panel">
          <p className="eyebrow">BYPASS INTELLIGENCE / VIETNAM</p>
          <h1>
            Route deviation
            <br />
            heatmap.
          </h1>
          <p className="map-description">
            Mỗi ô H3 thể hiện số chuyến đi đã bypass đoạn đường tương ứng. Màu
            càng đậm, volume bypass càng cao.
          </p>

          <form className="map-filters" onSubmit={applyFilters}>
            <div className="control-heading control-wide">
              <span>DATA FILTERS</span>
              {query.isFetching ? (
                <small>UPDATING...</small>
              ) : (
                <small
                  className={
                    (query.data?.responseMs ?? 0) < 2_000
                      ? "response-ok"
                      : "response-slow"
                  }
                >
                  {query.data
                    ? `${Math.round(query.data.responseMs)}MS`
                    : "READY"}
                </small>
              )}
            </div>
            <label>
              <span>FROM TIME</span>
              <input
                type="datetime-local"
                value={startTime}
                max={endTime || undefined}
                onChange={(event) => setStartTime(event.target.value)}
              />
            </label>
            <label>
              <span>TO TIME</span>
              <input
                type="datetime-local"
                value={endTime}
                min={startTime || undefined}
                onChange={(event) => setEndTime(event.target.value)}
              />
            </label>
            <label className="control-wide">
              <span>DRIVER UUID</span>
              <input
                type="text"
                value={driverId}
                placeholder="Tat ca driver"
                pattern={UUID_PATTERN.source}
                onChange={(event) => setDriverId(event.target.value)}
              />
            </label>
            <label className="control-wide">
              <span>H3 RESOLUTION</span>
              <select
                value={resolution}
                onChange={(event) => setResolution(Number(event.target.value))}
              >
                {[9, 10, 11, 12].map((value) => (
                  <option key={value} value={value}>
                    Resolution {value}
                  </option>
                ))}
              </select>
            </label>
            <div className="control-actions control-wide">
              <button type="submit">APPLY FILTERS</button>
              <button type="button" onClick={resetFilters}>
                RESET
              </button>
            </div>
          </form>

          <div className="map-view-toggle" aria-label="Che do hien thi ban do">
            <button
              className={viewMode === "h3-grid" ? "is-active" : undefined}
              type="button"
              aria-pressed={viewMode === "h3-grid"}
              onClick={() => handleViewMode("h3-grid")}
            >
              <span>H3 GRID</span>
              <small>Polygon detail</small>
            </button>
            <button
              className={viewMode === "heat-blur" ? "is-active" : undefined}
              type="button"
              aria-pressed={viewMode === "heat-blur"}
              onClick={() => handleViewMode("heat-blur")}
            >
              <span>HEAT BLUR</span>
              <small>Density overview</small>
            </button>
          </div>

          <div className="map-metrics">
            <article>
              <span>H3 CELLS</span>
              <strong>{cells.length}</strong>
            </article>
            <article>
              <span>TOTAL VOLUME</span>
              <strong>{totalVolume}</strong>
            </article>
            <article>
              <span>RESOLUTION</span>
              <strong>{resolutions.join(" · ") || "9–12"}</strong>
            </article>
          </div>

          <div className="map-legend">
            <div>
              <span>LOW · {minimumVolume}</span>
              <span>BYPASS TRIPS</span>
              <span>HIGH · {maximumVolume}</span>
            </div>
            <div className="map-legend__scale" />
          </div>

          {query.isLoading && (
            <div className="map-message">Đang tải dữ liệu heatmap…</div>
          )}
          {query.isError && (
            <div className="map-message map-message--error" role="alert">
              Không thể tải heatmap. {query.error.message}
              <button type="button" onClick={() => query.refetch()}>
                Thử lại
              </button>
            </div>
          )}
          {!query.isLoading && !query.isError && cells.length === 0 && (
            <div className="map-message">
              Chưa có dữ liệu H3. Bản đồ sẽ cập nhật khi pipeline tạo
              trip_route_hexes.
            </div>
          )}

          <section className="audit-panel">
            <div className="control-heading">
              <span>ROUTE AUDIT VIEW</span>
              <small>{auditQuery.data?.trip_status ?? "NO TRIP"}</small>
            </div>
            <form onSubmit={loadAudit}>
              <input
                type="text"
                aria-label="Trip UUID"
                placeholder="Nhap trip UUID"
                value={auditTripInput}
                pattern={UUID_PATTERN.source}
                required
                onChange={(event) => setAuditTripInput(event.target.value)}
              />
              <button type="submit">LOAD</button>
            </form>
            <div className="route-toggles">
              <label>
                <input
                  type="checkbox"
                  checked={showPlannedRoute}
                  onChange={(event) =>
                    setShowPlannedRoute(event.target.checked)
                  }
                />
                <span className="route-swatch route-swatch--planned" />
                Planned route
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={showActualRoute}
                  onChange={(event) => setShowActualRoute(event.target.checked)}
                />
                <span className="route-swatch route-swatch--actual" />
                Actual route
              </label>
            </div>
            {auditQuery.isLoading && <p>Dang tai route comparison...</p>}
            {auditQuery.isError && (
              <p className="audit-error" role="alert">
                Khong the tai audit data. Kiem tra trip UUID.
              </p>
            )}
            {auditQuery.data && (
              <dl className="audit-summary">
                <div>
                  <dt>Matched segments</dt>
                  <dd>{auditQuery.data.matched_segments.length}</dd>
                </div>
                <div>
                  <dt>GPS gaps</dt>
                  <dd>{auditQuery.data.total_gaps}</dd>
                </div>
              </dl>
            )}
          </section>

          {hoverInfo && (
            <dl className="hex-inspector">
              <div>
                <dt>H3 cell</dt>
                <dd>{hoverInfo.cell.hexId}</dd>
              </div>
              <div>
                <dt>Resolution</dt>
                <dd>{hoverInfo.cell.resolution}</dd>
              </div>
              <div>
                <dt>Bypass trips</dt>
                <dd>{hoverInfo.cell.bypassTripCount}</dd>
              </div>
            </dl>
          )}
        </aside>

        <section className="map-stage">
          <HeatmapMap
            cells={cells}
            viewMode={viewMode}
            auditData={auditQuery.data}
            showPlannedRoute={showPlannedRoute}
            showActualRoute={showActualRoute}
            onHover={handleHover}
          />
          {hoverInfo && viewMode === "h3-grid" && (
            <div
              className="map-tooltip"
              style={{ left: hoverInfo.x + 14, top: hoverInfo.y + 14 }}
            >
              <strong>{hoverInfo.cell.bypassTripCount}</strong>
              <span>bypass trips</span>
              <small>H3 res {hoverInfo.cell.resolution}</small>
            </div>
          )}
          <div className="map-stage__label">
            {viewMode === "h3-grid" ? "H3 POLYGON VIEW" : "HEAT BLUR OVERVIEW"}
            {" · "}AUTO REFRESH 30S
          </div>
        </section>
      </main>
    </div>
  );
}
