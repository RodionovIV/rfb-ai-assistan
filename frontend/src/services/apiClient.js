import axios from "axios";
import { getApiBaseUrl } from "../config/api";

const resolveBaseUrl = () => {
  const resolved = getApiBaseUrl();
  if (resolved) {
    return resolved;
  }
  if (typeof window !== "undefined" && window.location) {
    return `${window.location.protocol}//${window.location.host}`;
  }
  return "";
};

const apiClient = axios.create({
  baseURL: resolveBaseUrl(),
});

const formatRequestUrl = (config) => {
  const rawUrl = config?.url ?? "";
  const base = config?.baseURL ?? apiClient.defaults.baseURL ?? "";

  if (!rawUrl) {
    return base;
  }

  try {
    return new URL(rawUrl, base || undefined).toString();
  } catch {
    if (!base) return rawUrl;
    if (rawUrl.startsWith("/")) {
      return `${base.replace(/\/$/, "")}${rawUrl}`;
    }
    return `${base}${rawUrl}`;
  }
};

const summarizeData = (data) => {
  if (typeof FormData !== "undefined" && data instanceof FormData) {
    return "[FormData]";
  }
  if (typeof Blob !== "undefined" && data instanceof Blob) {
    return `[Blob size=${data.size}]`;
  }
  if (typeof data === "string") {
    return data.length > 200 ? `${data.slice(0, 200)}…` : data;
  }
  return data;
};

apiClient.interceptors.request.use((config) => {
  const method = (config.method ?? "GET").toUpperCase();
  const url = formatRequestUrl(config);
  const summary = summarizeData(config.data);
  if (summary === undefined) {
    console.log(`[API][REQUEST] ${method} ${url}`);
  } else {
    console.log(`[API][REQUEST] ${method} ${url}`, summary);
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    const method = (response.config?.method ?? "GET").toUpperCase();
    const url = formatRequestUrl(response.config ?? {});
    console.log(
      `[API][RESPONSE] ${response.status} ${method} ${url}`,
      summarizeData(response.data)
    );
    return response;
  },
  (error) => {
    const config = error.config ?? {};
    const method = (config.method ?? "GET").toUpperCase();
    const url = formatRequestUrl(config);

    if (error.response) {
      console.error(
        `[API][ERROR] ${error.response.status} ${method} ${url}`,
        summarizeData(error.response.data)
      );
    } else {
      console.error(`[API][ERROR] ${method} ${url}`, error.message ?? error);
    }

    return Promise.reject(error);
  }
);

export default apiClient;
