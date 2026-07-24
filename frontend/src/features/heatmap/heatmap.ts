import type { HeatmapFeature } from "../../api/client";

export interface H3Cell {
  hexId: string;
  resolution: number;
  bypassVolume: number;
}

export function toH3Cells(features: HeatmapFeature[]): H3Cell[] {
  return features.flatMap((feature) => {
    const { hex_id, h3_resolution, bypass_trip_count, heat_weight } =
      feature.properties;
    if (!hex_id || h3_resolution === undefined) return [];

    return [
      {
        hexId: hex_id,
        resolution: h3_resolution,
        bypassVolume: bypass_trip_count ?? heat_weight,
      },
    ];
  });
}

export function volumeColor(
  volume: number,
  maximum: number,
): [number, number, number, number] {
  const ratio = maximum > 0 ? Math.min(Math.max(volume / maximum, 0), 1) : 0;
  return [
    Math.round(255 - ratio * 20),
    Math.round(190 - ratio * 125),
    Math.round(72 - ratio * 35),
    Math.round(120 + ratio * 100),
  ];
}
