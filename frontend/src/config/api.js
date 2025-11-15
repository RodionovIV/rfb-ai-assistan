const rawApiUrl = (import.meta.env.VITE_API_URL ?? "").trim();
const cleanedApiUrl = rawApiUrl.endsWith("/") ? rawApiUrl.slice(0, -1) : rawApiUrl;

const rawPrefix = import.meta.env.VITE_API_PREFIX ?? "/api/v1";
const normalizedPrefix = rawPrefix.startsWith("/") ? rawPrefix : `/${rawPrefix}`;

export const API_BASE_URL = cleanedApiUrl;
export const API_PREFIX = normalizedPrefix;

const isLikelyInternalHostname = (hostname) => {
  if (!hostname) return false;
  if (hostname === "localhost" || hostname === "127.0.0.1") return false;
  if (hostname === "0.0.0.0") return true;
  return !hostname.includes(".");
};

const toOriginString = (url) => {
  const port = url.port ? `:${url.port}` : "";
  return `${url.protocol}//${url.hostname}${port}`;
};

export const getApiBaseUrl = () => {
  if (typeof window === "undefined" || !window.location) {
    return API_BASE_URL;
  }

  const windowOrigin = `${window.location.protocol}//${window.location.host}`;

  if (!API_BASE_URL) {
    return windowOrigin;
  }

  try {
    const parsed = new URL(API_BASE_URL, windowOrigin);

    if (isLikelyInternalHostname(parsed.hostname)) {
      const resolved = new URL(parsed.toString());
      resolved.hostname = window.location.hostname;
      return toOriginString(resolved);
    }

    return parsed.origin;
  } catch {
    if (API_BASE_URL.startsWith("/")) {
      return windowOrigin;
    }

    return API_BASE_URL;
  }
};

export const resolveApiUrl = (path = "") => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const baseUrl = getApiBaseUrl();

  if (!baseUrl) {
    return `${API_PREFIX}${normalizedPath === "/" ? "" : normalizedPath}`;
  }

  return `${baseUrl}${API_PREFIX}${normalizedPath === "/" ? "" : normalizedPath}`;
};
