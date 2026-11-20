// API client. Types mirror the backend schemas (app/schemas.py); the contract is published at /api/openapi.json.

export interface Note {
  id: number;
  title: string;
  body: string;
  created_at: string;
}

export interface NotePage {
  items: Note[];
  limit: number;
  offset: number;
}

/** RFC 9457 problem details, as returned by the backend for every error. */
export interface Problem {
  title: string;
  status: number;
  detail?: string;
  errors?: { loc: (string | number)[]; msg: string }[];
}

export class ApiError extends Error {
  readonly problem: Problem;

  constructor(problem: Problem) {
    super(problem.detail ?? problem.title);
    this.problem = problem;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { Accept: "application/json", "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const problem = (await response.json().catch(() => null)) as Problem | null;
    throw new ApiError(problem ?? { title: response.statusText, status: response.status });
  }
  return (await response.json()) as T;
}

export const listNotes = (): Promise<NotePage> => request<NotePage>("/api/v1/notes");

export const createNote = (title: string, body: string): Promise<Note> =>
  request<Note>("/api/v1/notes", { method: "POST", body: JSON.stringify({ title, body }) });
