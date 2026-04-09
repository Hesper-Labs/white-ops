import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryError } from "../QueryError";

describe("QueryError", () => {
  it("renders error message", () => {
    const error = new Error("Something failed");
    render(<QueryError error={error} />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Something failed")).toBeInTheDocument();
  });

  it("renders custom message when provided", () => {
    const error = new Error("Original");
    render(<QueryError error={error} message="Custom error message" />);

    expect(screen.getByText("Custom error message")).toBeInTheDocument();
  });

  it("renders retry button when onRetry provided", async () => {
    const user = userEvent.setup();
    const handleRetry = vi.fn();
    const error = new Error("Failed");

    render(<QueryError error={error} onRetry={handleRetry} />);

    const retryButton = screen.getByRole("button", { name: /retry/i });
    expect(retryButton).toBeInTheDocument();

    await user.click(retryButton);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it("does not render retry button when onRetry not provided", () => {
    render(<QueryError error={new Error("Oops")} />);

    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });

  it("shows network error variant", () => {
    const error = new Error("Network Error");
    render(<QueryError error={error} />);

    expect(screen.getByText("Connection Error")).toBeInTheDocument();
  });
});
