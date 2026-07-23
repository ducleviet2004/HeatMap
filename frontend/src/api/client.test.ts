import { describe, expect, it } from "vitest";
import { resolveApiBaseUrl } from "./client";

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
