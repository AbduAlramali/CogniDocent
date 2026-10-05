import axios from "axios";
import { toApiError } from "./errors";

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
    return Promise.reject(toApiError(error));
  }
);

