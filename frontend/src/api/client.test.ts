import { describe, expect, it } from "vitest";
import { heatmapQueryString, resolveApiBaseUrl } from "./client";

describe("API configuration", () => {
  it("normalizes an environment-provided URL", () => {
    expect(resolveApiBaseUrl("https://api.example.test/")).toBe(
      "https://api.example.test",
    );
  });

  it("supports a same-origin deployment when the value is absent", () => {
    expect(resolveApiBaseUrl(undefined)).toBe("");
  });
});

describe("heatmapQueryString", () => {
  it("maps dashboard filters to backend query parameter names", () => {
    expect(
      heatmapQueryString({
        startTime: "2026-07-01T00:00:00.000Z",
        endTime: "2026-07-24T23:59:59.000Z",
        driverId: "8aa2607f-e3a2-4ba7-908d-cf78fbd33c76",
        h3Resolution: 11,
      }),
    ).toBe(
      "start_time=2026-07-01T00%3A00%3A00.000Z&end_time=2026-07-24T23%3A59%3A59.000Z&driver_id=8aa2607f-e3a2-4ba7-908d-cf78fbd33c76&h3_resolution=11",
    );
  });
});
