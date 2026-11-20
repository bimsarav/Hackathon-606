import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, asList, qs, setToken, setUnauthorizedHandler } from '../lib/api';

afterEach(() => { vi.unstubAllGlobals(); });

function stub(status: number, body: unknown) {
  const f = vi.fn().mockResolvedValue(new Response(body === undefined ? null : JSON.stringify(body), { status }));
  vi.stubGlobal('fetch', f);
  return f;
}

describe('api client', () => {
  it('sends the bearer token and query string', async () => {
    setToken('abc.def.ghi');
    const f = stub(200, { items: [] });
    await api('/incidents', { query: { view: 'mine', q: '', page: 2 } });
    const [url, init] = f.mock.calls[0];
    expect(url).toBe('/api/v1/incidents?view=mine&page=2');
    expect((init.headers as Headers).get('Authorization')).toBe('Bearer abc.def.ghi');
  });
  it('clears the token and notifies on 401', async () => {
    setToken('t');
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    stub(401, { title: 'Unauthorized', status: 401 });
    await expect(api('/auth/me')).rejects.toBeInstanceOf(ApiError);
    expect(handler).toHaveBeenCalled();
    expect(sessionStorage.getItem('esm.token')).toBeNull();
  });
  it('surfaces problem+json with requestId', async () => {
    stub(422, { title: 'Unprocessable', status: 422, detail: 'Bad state', requestId: 'req-1' });
    const err = (await api('/x', { body: {} }).catch((e: unknown) => e)) as ApiError;
    expect(err.problem.requestId).toBe('req-1');
    expect(err.message).toBe('Bad state');
  });
  it('helpers', () => {
    expect(qs({ a: 1, b: undefined, c: false })).toBe('?a=1&c=false');
    expect(asList({ items: [1, 2] })).toEqual([1, 2]);
    expect(asList(undefined)).toEqual([]);
  });
});
