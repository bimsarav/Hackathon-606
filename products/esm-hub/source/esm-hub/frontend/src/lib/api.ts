export const TOKEN_KEY = 'esm.token';

export interface ProblemDetail { title?: string; status?: number; detail?: string; requestId?: string; errors?: unknown }

export class ApiError extends Error {
  status: number;
  problem: ProblemDetail;
  constructor(status: number, problem: ProblemDetail) {
    super(problem.detail || problem.title || `Request failed (${status})`);
    this.status = status;
    this.problem = problem;
  }
}

export function getToken(): string | null {
  try { return sessionStorage.getItem(TOKEN_KEY); } catch { return null; }
}
export function setToken(t: string | null): void {
  try { if (t) sessionStorage.setItem(TOKEN_KEY, t); else sessionStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ }
}

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(fn: () => void): void { onUnauthorized = fn; }

type Query = Record<string, string | number | boolean | null | undefined>;
export interface ApiOptions { method?: string; body?: unknown; query?: Query; idempotencyKey?: string; auth?: boolean }

export function qs(query?: Query): string {
  if (!query) return '';
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : '';
}

function buildHeaders(opts: ApiOptions): Headers {
  const h = new Headers({ Accept: 'application/json, application/problem+json' });
  if (opts.body !== undefined) h.set('Content-Type', 'application/json');
  const t = getToken();
  if (t && opts.auth !== false) h.set('Authorization', `Bearer ${t}`);
  if (opts.idempotencyKey) h.set('Idempotency-Key', opts.idempotencyKey);
  return h;
}

async function toError(res: Response): Promise<ApiError> {
  let problem: ProblemDetail = { title: res.statusText, status: res.status };
  try {
    const j = (await res.json()) as ProblemDetail;
    problem = { ...problem, ...j };
  } catch { /* non-JSON body */ }
  return new ApiError(res.status, problem);
}

export async function api<T = unknown>(path: string, opts: ApiOptions = {}): Promise<T> {
  const res = await fetch(`/api/v1${path}${qs(opts.query)}`, {
    method: opts.method ?? (opts.body !== undefined ? 'POST' : 'GET'),
    headers: buildHeaders(opts),
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 401 && opts.auth !== false) {
    setToken(null);
    onUnauthorized();
  }
  if (!res.ok) throw await toError(res);
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

/** Fetch a CSV export with the bearer token and hand it to the browser as a download. */
export async function download(path: string, query: Query | undefined, filename: string): Promise<void> {
  const res = await fetch(`/api/v1${path}${qs(query)}`, { headers: buildHeaders({ auth: true }) });
  if (res.status === 401) { setToken(null); onUnauthorized(); }
  if (!res.ok) throw await toError(res);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function newKey(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/** Accepts a plain array or a PageResponse. */
export function asList<T>(v: T[] | { items: T[] } | undefined | null): T[] {
  if (!v) return [];
  return Array.isArray(v) ? v : v.items ?? [];
}
