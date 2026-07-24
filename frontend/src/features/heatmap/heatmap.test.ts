import { describe, expect, it } from "vitest";
import type { HeatmapFeature } from "../../api/client";
import { toH3Cells, volumeColor } from "./heatmap";

describe("toH3Cells", () => {
  it("maps API heat weight to an H3 bypass volume", () => {
    const feature: HeatmapFeature = {
      type: "Feature",
      properties: {
        hex_id: "8965b56642fffff",
        h3_resolution: 9,
        heat_weight: 12,
        display_weight: 2.56,
      },
      geometry: { type: "Polygon", coordinates: [] },
    };

    expect(toH3Cells([feature])).toEqual([
      { hexId: "8965b56642fffff", resolution: 9, bypassVolume: 12 },
    ]);
  });

  it("ignores features without an H3 identifier", () => {
    const feature = {
      type: "Feature",
      properties: { heat_weight: 4, display_weight: 1.6 },
      geometry: { type: "Polygon", coordinates: [] },
    } satisfies HeatmapFeature;

    expect(toH3Cells([feature])).toEqual([]);
  });
});

describe("volumeColor", () => {
  it("uses a darker color for a larger bypass volume", () => {
    expect(volumeColor(10, 10)[1]).toBeLessThan(volumeColor(1, 10)[1]);
  });
});
