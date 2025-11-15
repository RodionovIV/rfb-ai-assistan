import axios from "axios";
import { getApiBaseUrl } from "./config/api";

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

axios.defaults.baseURL = resolveBaseUrl();

const formatRequestUrl = (config) => {
  const rawUrl = config?.url ?? "";
  if (!rawUrl) {
    return config?.baseURL ?? axios.defaults.baseURL ?? "";
  }

  try {
    return new URL(rawUrl, config?.baseURL ?? axios.defaults.baseURL ?? undefined).toString();
  } catch {
    const base = config?.baseURL ?? axios.defaults.baseURL ?? "";
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

axios.interceptors.request.use((config) => {
  const method = (config.method ?? "GET").toUpperCase();
  const url = formatRequestUrl(config);
  const summary = summarizeData(config.data);
  console.info(`[API][REQUEST] ${method} ${url}`, summary ?? "");
  return config;
});

axios.interceptors.response.use(
  (response) => {
    const method = (response.config?.method ?? "GET").toUpperCase();
    const url = formatRequestUrl(response.config ?? {});
    console.info(
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

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
