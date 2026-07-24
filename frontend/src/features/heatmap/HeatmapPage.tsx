import { useQuery } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";
import { heatmapApi } from "../../api/client";
import { HeatmapMap } from "./HeatmapMap";
import { toH3Cells, type H3Cell } from "./heatmap";

export function HeatmapPage() {
  const query = useQuery({
    queryKey: ["heatmap"],
    queryFn: heatmapApi.get,
    refetchInterval: 30_000,
  });
  const cells = useMemo(
    () => toH3Cells(query.data?.features ?? []),
    [query.data],
  );
  const [hoveredCell, setHoveredCell] = useState<H3Cell | null>(null);
  const handleHover = useCallback(
    (cell: H3Cell | null) => setHoveredCell(cell),
    [],
  );
  const totalVolume = cells.reduce((sum, cell) => sum + cell.bypassVolume, 0);
  const resolutions = [...new Set(cells.map((cell) => cell.resolution))].sort();

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
              <span>LOW</span>
              <span>HIGH</span>
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

          {hoveredCell && (
            <dl className="hex-inspector">
              <div>
                <dt>H3 cell</dt>
                <dd>{hoveredCell.hexId}</dd>
              </div>
              <div>
                <dt>Resolution</dt>
                <dd>{hoveredCell.resolution}</dd>
              </div>
              <div>
                <dt>Bypass trips</dt>
                <dd>{hoveredCell.bypassVolume}</dd>
              </div>
            </dl>
          )}
        </aside>

        <section className="map-stage">
          <HeatmapMap cells={cells} onHover={handleHover} />
          <div className="map-stage__label">
            LIVE H3 SURFACE · AUTO REFRESH 30S
          </div>
        </section>
      </main>
    </div>
  );
}
