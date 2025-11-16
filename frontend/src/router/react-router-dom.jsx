import {
  Children,
  createContext,
  isValidElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

const RouterContext = createContext(null);

const getLocationSnapshot = () => {
  if (typeof window === "undefined") {
    return { pathname: "/", search: "", hash: "" };
  }
  const { pathname, search, hash } = window.location;
  return { pathname, search, hash };
};

const toPathString = (to) => {
  if (typeof to === "string") return to || "/";
  if (to && typeof to === "object") {
    const { pathname = "/", search = "", hash = "" } = to;
    return `${pathname}${search}${hash}` || "/";
  }
  return "/";
};

const normalizeSegments = (value) =>
  value
    .replace(/(^\/|\/$)/g, "")
    .split("/")
    .filter(Boolean);

const matchPath = (pattern, pathname) => {
  if (!pattern) {
    return pathname === "/" ? { params: {} } : null;
  }

  if (pattern === "*") {
    return { params: {} };
  }

  const patternSegments = normalizeSegments(pattern);
  const pathSegments = normalizeSegments(pathname);

  const params = {};
  const maxLength = Math.max(patternSegments.length, pathSegments.length);

  for (let index = 0; index < maxLength; index += 1) {
    const patternSegment = patternSegments[index];
    const pathSegment = pathSegments[index];

    if (patternSegment === "*") {
      return { params };
    }

    if (patternSegment && patternSegment.startsWith(":")) {
      if (typeof pathSegment === "undefined") {
        return null;
      }
      const paramName = patternSegment.slice(1);
      params[paramName] = decodeURIComponent(pathSegment);
      continue;
    }

    if (patternSegment !== pathSegment) {
      return null;
    }
  }

  if (
    patternSegments[patternSegments.length - 1] !== "*" &&
    patternSegments.length !== pathSegments.length
  ) {
    return null;
  }

  return { params };
};

const useRouterContext = () => {
  const context = useContext(RouterContext);
  if (!context) {
    throw new Error("useRouter components must be rendered inside a <BrowserRouter>");
  }
  return context;
};

export function BrowserRouter({ children }) {
  const [location, setLocation] = useState(() => getLocationSnapshot());
  const [params, setParams] = useState({});

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handlePopState = () => {
      setLocation(getLocationSnapshot());
    };
    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  const navigate = useCallback((to, options = {}) => {
    if (typeof window === "undefined") return;
    const { replace = false, state } = options;
    const nextPath = toPathString(to);
    if (replace) {
      window.history.replaceState(state ?? {}, "", nextPath);
    } else {
      window.history.pushState(state ?? {}, "", nextPath);
    }
    setLocation(getLocationSnapshot());
  }, []);

  const value = useMemo(
    () => ({
      location,
      pathname: location.pathname,
      search: location.search,
      hash: location.hash,
      navigate,
      params,
      setParams,
    }),
    [location, navigate, params]
  );

  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
}

export function Routes({ children }) {
  const { pathname, setParams } = useRouterContext();
  const routeChildren = Children.toArray(children);

  let match = null;
  let element = null;

  for (const child of routeChildren) {
    if (!isValidElement(child)) continue;
    const { path = "*", element: routeElement } = child.props || {};
    const matchResult = matchPath(path, pathname);
    if (matchResult) {
      match = matchResult;
      element = routeElement ?? null;
      break;
    }
  }

  const previousParamsRef = useRef(null);

  useEffect(() => {
    const nextParams = match?.params ?? {};
    const prevParams = previousParamsRef.current;

    const hasChanged =
      !prevParams ||
      Object.keys(nextParams).length !== Object.keys(prevParams).length ||
      Object.keys(nextParams).some((key) => nextParams[key] !== prevParams[key]);

    if (hasChanged) {
      previousParamsRef.current = nextParams;
      setParams(nextParams);
    }
  }, [match, setParams]);

  return element;
}

export function Route() {
  return null;
}

export function Navigate({ to, replace = false, state }) {
  const navigate = useNavigate();
  useEffect(() => {
    navigate(to, { replace, state });
  }, [navigate, replace, state, to]);
  return null;
}

export function useNavigate() {
  const { navigate } = useRouterContext();
  return navigate;
}

export function useParams() {
  const { params } = useRouterContext();
  return params;
}

export function useLocation() {
  const { location } = useRouterContext();
  return location;
}

export function Link({ to, replace = false, state, onClick, ...rest }) {
  const navigate = useNavigate();
  const href = toPathString(to);

  const handleClick = useCallback(
    (event) => {
      if (onClick) {
        onClick(event);
      }
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.altKey ||
        event.ctrlKey ||
        event.shiftKey
      ) {
        return;
      }
      event.preventDefault();
      navigate(to, { replace, state });
    },
    [navigate, onClick, replace, state, to]
  );

  return <a href={href} onClick={handleClick} {...rest} />;
}

export default {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Link,
  useNavigate,
  useParams,
  useLocation,
};
