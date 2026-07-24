import { describe, expect, it } from "vitest";
import type { HeatmapFeature } from "../../api/client";
import { polygonCenter, toH3Cells, volumeColor } from "./heatmap";

describe("toH3Cells", () => {
  it("maps API heat weight to an H3 bypass volume", () => {
    const feature: HeatmapFeature = {
      type: "Feature",
      properties: {
        hex_id: "8965b56642fffff",
        h3_resolution: 9,
        bypass_trip_count: 7,
        heat_weight: 12,
        display_weight: 2.56,
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [105, 21],
            [107, 21],
            [107, 23],
            [105, 23],
            [105, 21],
          ],
        ],
      },
    };

    expect(toH3Cells([feature])).toEqual([
      {
        hexId: "8965b56642fffff",
        resolution: 9,
        bypassTripCount: 7,
        center: [106, 22],
      },
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

describe("polygonCenter", () => {
  it("does not count the duplicated closing coordinate twice", () => {
    expect(
      polygonCenter([
        [0, 0],
        [2, 0],
        [2, 2],
        [0, 2],
        [0, 0],
      ]),
    ).toEqual([1, 1]);
  });
});

describe("volumeColor", () => {
  it("uses a darker color for a larger bypass volume", () => {
    expect(volumeColor(10, 10)[1]).toBeLessThan(volumeColor(1, 10)[1]);
  });
});
