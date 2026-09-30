export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type JsonValue = Record<string, unknown> | unknown[] | string | number | boolean | null;

export async function api<T>(
  path: string,
  init: RequestInit & { json?: JsonValue } = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  let body = init.body;

  if (init.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }

  const response = await fetch(path, {
    ...init,
    body,
    headers,
    credentials: "same-origin",
  });

  if (!response.ok) {
    let detail = "request_failed";
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? detail;
    } catch {
      // Keep the stable fallback detail.
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
