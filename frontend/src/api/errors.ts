export type ErrorCode =
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'VALIDATION'
  | 'SERVER_ERROR'
  | 'NETWORK_ERROR'
  | 'UNKNOWN';

export interface ApiError {
  status: number;
  code: ErrorCode;
  message: string;
  fieldErrors?: Record<string, string[]>;
  retryable: boolean;
  correlationId?: string;
}

export class ApiErrorException extends Error {
  constructor(public readonly error: ApiError) {
    super(error.message);
    this.name = 'ApiErrorException';
  }
}

export function normalizeError(response: Response | null, body: unknown): ApiError {
  const status = response?.status ?? 0;
  const correlationId = response?.headers.get('x-request-id') ?? undefined;

  if (status === 401) {
    return {
      status,
      code: 'UNAUTHORIZED',
      message: 'Your session has expired. Please sign in again.',
      retryable: false,
      correlationId,
    };
  }

  if (status === 403) {
    return {
      status,
      code: 'FORBIDDEN',
      message: 'You do not have permission to access this resource.',
      retryable: false,
      correlationId,
    };
  }

  if (status === 404) {
    return {
      status,
      code: 'NOT_FOUND',
      message: 'The requested resource was not found.',
      retryable: false,
      correlationId,
    };
  }

  if (status === 409) {
    return {
      status,
      code: 'CONFLICT',
      message: 'This action conflicts with the current state. Please refresh and try again.',
      retryable: true,
      correlationId,
    };
  }

  if (status === 422) {
    const fieldErrors = extractFieldErrors(body);
    return {
      status,
      code: 'VALIDATION',
      message: 'Please fix the validation errors and try again.',
      fieldErrors,
      retryable: false,
      correlationId,
    };
  }

  if (status === 429) {
    return {
      status,
      code: 'SERVER_ERROR',
      message: 'Too many requests. Please wait a moment and try again.',
      retryable: true,
      correlationId,
    };
  }

  if (status >= 500) {
    return {
      status,
      code: 'SERVER_ERROR',
      message: 'Something went wrong on our end. Please try again later.',
      retryable: true,
      correlationId,
    };
  }

  if (status === 0) {
    return {
      status: 0,
      code: 'NETWORK_ERROR',
      message: 'Unable to connect to the server. Please check your connection.',
      retryable: true,
      correlationId,
    };
  }

  return {
    status,
    code: 'UNKNOWN',
    message: 'An unexpected error occurred.',
    retryable: false,
    correlationId,
  };
}

function extractFieldErrors(body: unknown): Record<string, string[]> | undefined {
  if (typeof body !== 'object' || body === null) return undefined;
  const b = body as Record<string, unknown>;
  if (Array.isArray(b.detail)) {
    const errors: Record<string, string[]> = {};
    for (const item of b.detail) {
      if (
        typeof item === 'object' &&
        item !== null &&
        'loc' in item &&
        'msg' in item
      ) {
        const loc = (item as Record<string, unknown>).loc as string[];
        const msg = (item as Record<string, unknown>).msg as string;
        if (loc && loc.length > 1) {
          const key = loc[loc.length - 1];
          if (!errors[key]) errors[key] = [];
          errors[key].push(msg);
        }
      }
    }
    return Object.keys(errors).length > 0 ? errors : undefined;
  }
  return undefined;
}
