const rawApiUrl = import.meta.env.VITE_API_URL ?? "";
const cleanedApiUrl = rawApiUrl.endsWith("/") ? rawApiUrl.slice(0, -1) : rawApiUrl;

const rawPrefix = import.meta.env.VITE_API_PREFIX ?? "/api/v1";
const normalizedPrefix = rawPrefix.startsWith("/") ? rawPrefix : `/${rawPrefix}`;

export const API_BASE_URL = cleanedApiUrl;
export const API_PREFIX = normalizedPrefix;

export const resolveApiUrl = (path = "") => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (!API_BASE_URL) {
    return `${API_PREFIX}${normalizedPath === "/" ? "" : normalizedPath}`;
  }
  return `${API_BASE_URL}${API_PREFIX}${normalizedPath === "/" ? "" : normalizedPath}`;
};
