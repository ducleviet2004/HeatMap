import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SystemStatusPage } from "./SystemStatusPage";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <SystemStatusPage />
    </QueryClientProvider>,
  );
}

describe("SystemStatusPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("shows loading state", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => undefined)),
    );
    renderPage();
    expect(screen.getByText("Running dependency checks…")).toBeInTheDocument();
  });

  it("shows degraded dependency and versions", async () => {
    const payloads = [
      { status: "ok", service: "route-deviation-api", version: "0.1.0" },
      {
        status: "degraded",
        dependencies: {
          database: { status: "ok", detail: null },
          osrm: {
            status: "not_configured",
            detail: "No local routing graph configured",
          },
        },
      },
      {
        application: "0.1.0",
        environment: "test",
        git_sha: "abc123",
        algorithm: "unimplemented",
        threshold_config: "v1",
        routing_data: "not_configured",
      },
    ];
    let index = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => payloads[index++] })),
    );
    renderPage();
    expect(await screen.findByText("DEGRADED")).toBeInTheDocument();
    expect(screen.getByText("OSRM Routing")).toBeInTheDocument();
    expect(screen.getByText("abc123")).toBeInTheDocument();
  });

  it.each([
    ["healthy", "HEALTHY"],
    ["unavailable", "UNAVAILABLE"],
  ])("shows %s overall state", async (state, label) => {
    const payloads = [
      { status: "ok", service: "route-deviation-api", version: "0.1.0" },
      {
        status: state,
        dependencies: {
          database: {
            status: state === "healthy" ? "ok" : "unavailable",
            detail: null,
          },
        },
      },
      {
        application: "0.1.0",
        environment: "test",
        git_sha: "abc123",
        algorithm: "unimplemented",
        threshold_config: "v1",
        routing_data: "not_configured",
      },
    ];
    let index = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => payloads[index++] })),
    );
    renderPage();
    expect(await screen.findByText(label)).toBeInTheDocument();
  });

  it("shows API error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 503, json: async () => ({}) })),
    );
    renderPage();
    expect(
      await screen.findByText("Status API unavailable."),
    ).toBeInTheDocument();
  });
});
