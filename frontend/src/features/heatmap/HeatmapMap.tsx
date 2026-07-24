import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import type { H3Cell } from "./heatmap";
import { volumeColor } from "./heatmap";

interface HeatmapMapProps {
  cells: H3Cell[];
  onHover: (cell: H3Cell | null) => void;
}

const HANOI_CENTER: [number, number] = [105.8542, 21.0285];

export function HeatmapMap({ cells, onHover }: HeatmapMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      center: HANOI_CENTER,
      zoom: 11,
      minZoom: 4,
      maxZoom: 18,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
    });
    map.addControl(new maplibregl.NavigationControl(), "bottom-right");

    const overlay = new MapboxOverlay({ interleaved: true, layers: [] });
    map.addControl(overlay);
    mapRef.current = map;
    overlayRef.current = overlay;

    return () => {
      overlay.finalize();
      map.remove();
      overlayRef.current = null;
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const maximum = Math.max(...cells.map((cell) => cell.bypassVolume), 0);
    const layer = new H3HexagonLayer<H3Cell>({
      id: "bypass-h3-cells",
      data: cells,
      pickable: true,
      extruded: false,
      getHexagon: (cell) => cell.hexId,
      getFillColor: (cell) => volumeColor(cell.bypassVolume, maximum),
      getLineColor: [255, 232, 176, 180],
      getLineWidth: 1,
      lineWidthMinPixels: 0.7,
      opacity: 0.9,
      onHover: ({ object }) => onHover(object ?? null),
      updateTriggers: { getFillColor: maximum },
    });
    overlayRef.current?.setProps({ layers: [layer] });
  }, [cells, onHover]);

  return (
    <div
      className="heatmap-canvas"
      ref={containerRef}
      aria-label="Bản đồ H3 bypass"
    />
  );
}
