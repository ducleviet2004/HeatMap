import type { HeatmapFeature } from "../../api/client";

export interface H3Cell {
  hexId: string;
  resolution: number;
  bypassTripCount: number;
  center: [number, number] | null;
}

export function toH3Cells(features: HeatmapFeature[]): H3Cell[] {
  // Tao mot data model dung chung cho ca H3 Grid va Heat Blur.
  return features.flatMap((feature) => {
    const { hex_id, h3_resolution, bypass_trip_count, heat_weight } =
      feature.properties;
    if (!hex_id || h3_resolution === undefined) return [];

    return [
      {
        hexId: hex_id,
        resolution: h3_resolution,
        bypassTripCount: bypass_trip_count ?? heat_weight,
        center: polygonCenter(feature.geometry.coordinates[0]),
      },
    ];
  });
}

export function polygonCenter(
  ring: number[][] | undefined,
): [number, number] | null {
  if (!ring?.length) return null;

  // API tra H3 Polygon; center duoc dung lam input point cho MapLibre Heatmap.
  const uniquePoints =
    ring.length > 1 &&
    ring[0][0] === ring[ring.length - 1][0] &&
    ring[0][1] === ring[ring.length - 1][1]
      ? ring.slice(0, -1)
      : ring;
  if (!uniquePoints.length) return null;

  const [longitude, latitude] = uniquePoints.reduce(
    ([longitudeSum, latitudeSum], point) => [
      longitudeSum + point[0],
      latitudeSum + point[1],
    ],
    [0, 0],
  );
  return [longitude / uniquePoints.length, latitude / uniquePoints.length];
}

export function volumeColor(
  volume: number,
  maximum: number,
): [number, number, number, number] {
  // Clamp ratio trong khoang 0..1 de RGBA color luon hop le.
  const ratio = maximum > 0 ? Math.min(Math.max(volume / maximum, 0), 1) : 0;
  return [
    Math.round(255 - ratio * 20),
    Math.round(190 - ratio * 125),
    Math.round(72 - ratio * 35),
    Math.round(120 + ratio * 100),
  ];
}
