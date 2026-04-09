import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// Track if we're already redirecting to prevent multiple 401 redirects
let isRedirecting = false;

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("whiteops_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !isRedirecting) {
      isRedirecting = true;
      localStorage.removeItem("whiteops_token");
      localStorage.removeItem("whiteops_demo");
      window.location.href = "/login";
      // Reset flag after navigation
      setTimeout(() => { isRedirecting = false; }, 1000);
    }
    return Promise.reject(error);
  },
);

export default api;
