import { getTokens, setTokens, clearAuth, type TokenPair } from '../auth/store';
import { ApiErrorException, normalizeError } from './errors';
import type { ApiError } from './errors';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';
const REQUEST_TIMEOUT = 30_000;

let isRefreshing = false;
let refreshPromise: Promise<TokenPair | null> | null = null;

async function fetchWithTimeout(
  input: RequestInfo,
  init: RequestInit & { timeout?: number } = {}
): Promise<Response> {
  const { timeout = REQUEST_TIMEOUT, ...rest } = init;
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(input, {
      ...rest,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(id);
  }
}

async function doRefresh(): Promise<TokenPair | null> {
  const tokens = getTokens();
  if (!tokens?.refresh_token) return null;

  try {
    const response = await fetchWithTimeout(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: tokens.refresh_token }),
      timeout: 10_000,
    });

    if (!response.ok) return null;

    const data = (await response.json()) as TokenPair;
    setTokens(data);
    return data;
  } catch {
    return null;
  }
}

async function refreshTokens(): Promise<TokenPair | null> {
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }
  isRefreshing = true;
  refreshPromise = doRefresh().finally(() => {
    isRefreshing = false;
    refreshPromise = null;
  });
  return refreshPromise;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: { signal?: AbortSignal; skipAuth?: boolean } = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = {
    Accept: 'application/json',
  };

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  if (!options.skipAuth) {
    const tokens = getTokens();
    if (tokens?.access_token) {
      headers['Authorization'] = `Bearer ${tokens.access_token}`;
    }
  }

  let response: Response;
  try {
    response = await fetchWithTimeout(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: options.signal,
    });
  } catch (err) {
    const error = normalizeError(null, null);
    throw new ApiErrorException(error);
  }

  // Handle 401 by attempting refresh once
  if (response.status === 401 && !options.skipAuth) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${refreshed.access_token}`;
      try {
        response = await fetchWithTimeout(url, {
          method,
          headers,
          body: body !== undefined ? JSON.stringify(body) : undefined,
          signal: options.signal,
        });
      } catch (err) {
        const error = normalizeError(null, null);
        throw new ApiErrorException(error);
      }
    } else {
      clearAuth();
      window.location.href = '/login';
      const error = normalizeError(response, null);
      throw new ApiErrorException(error);
    }
  }

  if (!response.ok) {
    let bodyData: unknown = null;
    try {
      bodyData = await response.json();
    } catch {
      // ignore
    }
    const error = normalizeError(response, bodyData);
    throw new ApiErrorException(error);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  const data = (await response.json()) as T;
  return data;
}

export { ApiErrorException };

export const api = {
  get<T>(path: string, options?: { signal?: AbortSignal }): Promise<T> {
    return request<T>('GET', path, undefined, options);
  },

  post<T>(path: string, body?: unknown, options?: { signal?: AbortSignal }): Promise<T> {
    return request<T>('POST', path, body, options);
  },

  patch<T>(path: string, body?: unknown, options?: { signal?: AbortSignal }): Promise<T> {
    return request<T>('PATCH', path, body, options);
  },

  del<T>(path: string, options?: { signal?: AbortSignal }): Promise<T> {
    return request<T>('DELETE', path, undefined, options);
  },
};

export type { ApiError, TokenPair };
