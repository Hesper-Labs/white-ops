import { create } from "zustand";
import { authApi } from "../api/endpoints";
import { mockApi } from "../api/mock";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  demoMode: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem("whiteops_token"),
  isLoading: true,
  demoMode: localStorage.getItem("whiteops_demo") === "true",
  error: null,

  login: async (email: string, password: string) => {
    set({ error: null, isLoading: true });
    try {
      const response = await authApi.login(email, password);
      const { access_token } = response.data;
      localStorage.setItem("whiteops_token", access_token);
      localStorage.removeItem("whiteops_demo");
      set({ token: access_token });

      const meResponse = await authApi.me();
      set({ user: meResponse.data, isLoading: false, demoMode: false, error: null });
    } catch (err) {
      const axiosError = err as { response?: { status: number; data?: { detail?: string } }; code?: string };

      // Distinguish between auth failure and server unavailable
      if (axiosError.response?.status === 401 || axiosError.response?.status === 422) {
        set({ isLoading: false, error: "Invalid email or password" });
        throw new Error("Invalid email or password");
      }

      if (axiosError.response?.status === 423) {
        set({ isLoading: false, error: "Account locked due to too many failed attempts" });
        throw new Error("Account locked");
      }

      if (axiosError.response?.status === 503) {
        set({ isLoading: false, error: "Service temporarily unavailable. Please try again." });
        throw new Error("Service unavailable");
      }

      // Backend truly not available - enter demo mode with explicit warning
      const demoAuth = await mockApi.auth.login();
      localStorage.setItem("whiteops_token", demoAuth.data.access_token);
      localStorage.setItem("whiteops_demo", "true");
      const demoUser = await mockApi.auth.me();
      set({
        user: demoUser.data,
        token: demoAuth.data.access_token,
        isLoading: false,
        demoMode: true,
        error: null,
      });
    }
  },

  logout: () => {
    localStorage.removeItem("whiteops_token");
    localStorage.removeItem("whiteops_demo");
    set({ user: null, token: null, demoMode: false });
  },

  checkAuth: async () => {
    const token = localStorage.getItem("whiteops_token");
    if (!token) {
      set({ isLoading: false });
      return;
    }
    try {
      const response = await authApi.me();
      set({ user: response.data, token, isLoading: false, demoMode: false });
    } catch {
      const state = useAuthStore.getState();
      if (state.demoMode) {
        const demoUser = await mockApi.auth.me();
        set({ user: demoUser.data, token, isLoading: false, demoMode: true });
      } else {
        localStorage.removeItem("whiteops_token");
        set({ user: null, token: null, isLoading: false });
      }
    }
  },
}));
