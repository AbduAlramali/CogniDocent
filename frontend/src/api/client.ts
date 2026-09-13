import axios from "axios";

export const getBaseApiUrl = (): string => {
  if (typeof window !== "undefined" && (window as any)._env_?.VITE_API_URL) {
    return (window as any)._env_.VITE_API_URL;
  }
  return "/api/v1";
};

export const apiClient = axios.create({
  baseURL: getBaseApiUrl(),
  headers: {
    "Content-Type": "application/json",
  },
});

// Update baseURL dynamically on request if window._env_ was populated after load
apiClient.interceptors.request.use((config) => {
  config.baseURL = getBaseApiUrl();
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "An unexpected network error occurred";
    return Promise.reject(new Error(message));
  }
);
