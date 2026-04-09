import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import NotFound from "../NotFound";

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

describe("NotFound", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders 404 text", () => {
    render(<NotFound />);

    expect(screen.getByText("404")).toBeInTheDocument();
    expect(screen.getByText("Page Not Found")).toBeInTheDocument();
  });

  it("has navigation buttons", async () => {
    const user = userEvent.setup();
    render(<NotFound />);

    const goBackButton = screen.getByRole("button", { name: /go back/i });
    const dashboardButton = screen.getByRole("button", { name: /dashboard/i });

    expect(goBackButton).toBeInTheDocument();
    expect(dashboardButton).toBeInTheDocument();

    await user.click(goBackButton);
    expect(mockNavigate).toHaveBeenCalledWith(-1);

    await user.click(dashboardButton);
    expect(mockNavigate).toHaveBeenCalledWith("/");
  });
});
