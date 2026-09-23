import { getAccessToken, clearSession } from '@/lib/auth/token';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// Normalize base URL: strip trailing slashes, fallback to production backend if unset
const RAW_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://rrb-alp-web.onrender.com';
export const API_BASE_URL = RAW_BASE_URL.replace(/\/+$/, '');

export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === 'true';

interface FetchApiOptions extends Omit<RequestInit, 'body'> {
  body?: any;
  params?: Record<string, string | number | boolean | undefined | null>;
  skipAuth?: boolean;
}

async function handleResponse(response: Response) {
  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const data = isJson ? await response.json() : null;

  if (!response.ok) {
    let message = (data && (data.message || data.detail || data.error)) || response.statusText;

    if (Array.isArray(data?.detail)) {
      // Format FastAPI 422 validation errors
      message = data.detail.map((d: any) => d.msg || `${d.loc?.join('.')}: invalid`).join(', ');
    }

    if (response.status === 401) {
      clearSession();
      // Handle session expiration gracefully
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        // Optional redirect or trigger event
      }
    } else if (response.status === 403) {
      message = 'Access denied. You do not have permission to perform this action.';
    } else if (response.status === 409) {
      message = message || 'A conflicting attempt or resource already exists.';
    } else if (response.status >= 500) {
      message = 'The server encountered an error. Please try again shortly.';
    }

    throw new ApiError(message, response.status, data);
  }

  return data;
}

export async function fetchApi<T>(endpoint: string, options: FetchApiOptions = {}): Promise<T> {
  const { body, params, skipAuth = false, headers: customHeaders = {}, ...restOptions } = options;

  let urlPath = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

  // Attach query parameters if provided
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        searchParams.append(key, String(val));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      urlPath += `${urlPath.includes('?') ? '&' : '?'}${queryString}`;
    }
  }

  const url = `${API_BASE_URL}${urlPath}`;

  const token = !skipAuth ? getAccessToken() : null;

  const headers: Record<string, string> = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(customHeaders as Record<string, string>),
  };

  let requestBody: any = undefined;

  if (body !== undefined) {
    if (body instanceof FormData) {
      // When body is FormData, let the browser set boundary Content-Type
      requestBody = body;
    } else if (typeof body === 'string') {
      headers['Content-Type'] = 'application/json';
      requestBody = body;
    } else {
      headers['Content-Type'] = 'application/json';
      requestBody = JSON.stringify(body);
    }
  }

  try {
    const response = await fetch(url, {
      ...restOptions,
      headers,
      body: requestBody,
    });
    return await handleResponse(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError('Unable to connect to backend server. Please check your connection.', 0);
  }
}
