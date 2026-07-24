import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import type { H3Cell } from "./heatmap";
import { volumeColor } from "./heatmap";

interface HeatmapMapProps {
  cells: H3Cell[];
  viewMode: HeatmapViewMode;
  onHover: (cell: H3Cell | null) => void;
}

export type HeatmapViewMode = "h3-grid" | "heat-blur";

const VIETNAM_CENTER: [number, number] = [106.5, 16.2];
const HEATMAP_SOURCE_ID = "bypass-heat-points";
const HEATMAP_LAYER_ID = "bypass-heat-blur";

function heatmapGeoJson(cells: H3Cell[]) {
  return {
    type: "FeatureCollection" as const,
    features: cells.flatMap((cell) =>
      cell.center
        ? [
            {
              type: "Feature" as const,
              properties: { bypassTripCount: cell.bypassTripCount },
              geometry: {
                type: "Point" as const,
                coordinates: cell.center,
              },
            },
          ]
        : [],
    ),
  };
}

function addHeatBlurLayer(map: maplibregl.Map) {
  if (map.getSource(HEATMAP_SOURCE_ID)) return;

  // Native MapLibre Heatmap tao blur overview tu center cua tung H3 cell.
  map.addSource(HEATMAP_SOURCE_ID, {
    type: "geojson",
    data: heatmapGeoJson([]),
  });
  map.addLayer({
    id: HEATMAP_LAYER_ID,
    type: "heatmap",
    source: HEATMAP_SOURCE_ID,
    maxzoom: 16,
    paint: {
      "heatmap-weight": [
        "interpolate",
        ["linear"],
        ["get", "bypassTripCount"],
        0,
        0,
        50,
        1,
      ],
      "heatmap-intensity": [
        "interpolate",
        ["linear"],
        ["zoom"],
        4,
        0.7,
        13,
        1.8,
      ],
      "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 4, 14, 13, 44],
      "heatmap-color": [
        "interpolate",
        ["linear"],
        ["heatmap-density"],
        0,
        "rgba(255,190,72,0)",
        0.25,
        "rgba(255,190,72,0.65)",
        0.55,
        "rgba(246,135,53,0.82)",
        0.8,
        "rgba(235,65,37,0.92)",
        1,
        "rgba(155,20,20,1)",
      ],
      "heatmap-opacity": 0,
    },
  });
}

export function HeatmapMap({ cells, viewMode, onHover }: HeatmapMapProps) {
  // mapRef va overlayRef giu instance giua cac lan React re-render.
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const heatOpacityRef = useRef(0);
  const heatAnimationRef = useRef<number | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    // MapLibre ve basemap OSM; Deck.gl overlay se ve H3 layer o phia tren.
    const map = new maplibregl.Map({
      container: containerRef.current,
      center: VIETNAM_CENTER,
      zoom: 4.7,
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
    map.on("load", () => addHeatBlurLayer(map));

    const overlay = new MapboxOverlay({ interleaved: true, layers: [] });
    map.addControl(overlay);
    mapRef.current = map;
    overlayRef.current = overlay;

    return () => {
      // Cleanup WebGL resource khi component unmount de tranh memory leak.
      overlay.finalize();
      map.remove();
      overlayRef.current = null;
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    // Chuan hoa volume theo cell lon nhat de tao color scale de doc.
    const maximum = Math.max(...cells.map((cell) => cell.bypassTripCount), 0);
    const layer = new H3HexagonLayer<H3Cell>({
      id: "bypass-h3-cells",
      data: cells,
      pickable: viewMode === "h3-grid",
      extruded: false,
      getHexagon: (cell) => cell.hexId,
      // bypassTripCount cang lon thi mau cell cang dam.
      getFillColor: (cell) => volumeColor(cell.bypassTripCount, maximum),
      getLineColor: [255, 232, 176, 180],
      getLineWidth: 1,
      lineWidthMinPixels: 0.7,
      opacity: viewMode === "h3-grid" ? 0.9 : 0,
      onHover: ({ object }) => onHover(object ?? null),
      updateTriggers: { getFillColor: maximum },
      transitions: { opacity: 350 },
    });
    overlayRef.current?.setProps({ layers: [layer] });
  }, [cells, onHover, viewMode]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const syncHeatBlur = () => {
      addHeatBlurLayer(map);
      const source = map.getSource(HEATMAP_SOURCE_ID) as
        | maplibregl.GeoJSONSource
        | undefined;
      source?.setData(heatmapGeoJson(cells));

      // Fade opacity trong 350ms de chuyen mode khong bi giat.
      if (heatAnimationRef.current !== null) {
        cancelAnimationFrame(heatAnimationRef.current);
      }
      const startOpacity = heatOpacityRef.current;
      const targetOpacity = viewMode === "heat-blur" ? 0.88 : 0;
      const startedAt = performance.now();
      const animateOpacity = (now: number) => {
        const progress = Math.min((now - startedAt) / 350, 1);
        const opacity =
          startOpacity + (targetOpacity - startOpacity) * progress;
        heatOpacityRef.current = opacity;
        map.setPaintProperty(HEATMAP_LAYER_ID, "heatmap-opacity", opacity);
        if (progress < 1) {
          heatAnimationRef.current = requestAnimationFrame(animateOpacity);
        } else {
          heatAnimationRef.current = null;
        }
      };
      heatAnimationRef.current = requestAnimationFrame(animateOpacity);
    };

    if (map.loaded()) syncHeatBlur();
    else map.once("load", syncHeatBlur);

    return () => {
      map.off("load", syncHeatBlur);
      if (heatAnimationRef.current !== null) {
        cancelAnimationFrame(heatAnimationRef.current);
        heatAnimationRef.current = null;
      }
    };
  }, [cells, viewMode]);

  return (
    <div
      className="heatmap-canvas"
      ref={containerRef}
      aria-label={
        viewMode === "h3-grid" ? "Ban do H3 polygon" : "Ban do heat blur"
      }
    />
  );
}
