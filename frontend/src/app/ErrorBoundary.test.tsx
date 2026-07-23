import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

function BrokenComponent(): never {
  throw new Error("synthetic render failure");
}

it("renders a safe recovery screen after an unexpected render error", () => {
  vi.spyOn(console, "error").mockImplementation(() => undefined);
  render(
    <ErrorBoundary>
      <BrokenComponent />
    </ErrorBoundary>,
  );
  expect(
    screen.getByText("The status console could not render."),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Reload console" }),
  ).toBeInTheDocument();
});
