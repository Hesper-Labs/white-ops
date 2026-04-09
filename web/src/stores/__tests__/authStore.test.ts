import { describe, it, expect, vi, beforeEach } from "vitest";
import { useAuthStore } from "../authStore";

// Mock the API modules
vi.mock("../../api/endpoints", () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
  },
}));

vi.mock("../../api/mock", () => ({
  mockApi: {
    auth: {
      login: vi.fn(),
      me: vi.fn(),
    },
  },
}));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { authApi } = await import("../../api/endpoints");

describe("authStore", () => {
  beforeEach(() => {
    // Reset Zustand store to initial state
    useAuthStore.setState({
      user: null,
      token: null,
      isLoading: true,
      demoMode: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it("initial state has no user", () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.error).toBeNull();
  });

  it("login success sets user and token", async () => {
    const mockToken = "test-jwt-token";
    const mockUser = {
      id: "1",
      email: "admin@test.com",
      full_name: "Admin User",
      role: "admin",
    };

    vi.mocked(authApi.login).mockResolvedValueOnce({
      data: { access_token: mockToken },
    });
    vi.mocked(authApi.me).mockResolvedValueOnce({ data: mockUser });

    await useAuthStore.getState().login("admin@test.com", "password123");

    const state = useAuthStore.getState();
    expect(state.user).toEqual(mockUser);
    expect(state.token).toBe(mockToken);
    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
    expect(state.demoMode).toBe(false);
    expect(localStorage.getItem("whiteops_token")).toBe(mockToken);
  });

  it("logout clears state", () => {
    // Set up an authenticated state first
    useAuthStore.setState({
      user: { id: "1", email: "a@b.com", full_name: "Test", role: "admin" },
      token: "some-token",
      demoMode: false,
      isLoading: false,
      error: null,
    });
    localStorage.setItem("whiteops_token", "some-token");

    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(state.demoMode).toBe(false);
    expect(localStorage.getItem("whiteops_token")).toBeNull();
  });

  it("checkAuth with no token sets isLoading false", async () => {
    useAuthStore.setState({ isLoading: true, token: null });
    // Ensure no token in localStorage
    localStorage.removeItem("whiteops_token");

    await useAuthStore.getState().checkAuth();

    const state = useAuthStore.getState();
    expect(state.isLoading).toBe(false);
    expect(state.user).toBeNull();
  });
});
