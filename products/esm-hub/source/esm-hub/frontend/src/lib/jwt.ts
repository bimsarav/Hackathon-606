export interface Claims { sub: string; cid?: number; roles: string[]; teams: number[]; name: string; email: string; exp?: number }

function b64urlDecode(s: string): string {
  const pad = s.length % 4 === 0 ? '' : '='.repeat(4 - (s.length % 4));
  const bin = atob(s.replace(/-/g, '+').replace(/_/g, '/') + pad);
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

/** Decode (not verify) the payload of a JWT. Returns null for malformed tokens. */
export function decodeToken(token: string | null): Claims | null {
  if (!token) return null;
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  try {
    const p = JSON.parse(b64urlDecode(parts[1])) as Record<string, unknown>;
    const toArr = (v: unknown) => (Array.isArray(v) ? v : []);
    return {
      sub: String(p.sub ?? ''),
      cid: typeof p.cid === 'number' ? p.cid : undefined,
      roles: toArr(p.roles).map(String),
      teams: toArr(p.teams).map(Number),
      name: String(p.name ?? ''),
      email: String(p.email ?? ''),
      exp: typeof p.exp === 'number' ? p.exp : undefined,
    };
  } catch {
    return null;
  }
}

export function isExpired(c: Claims | null, nowMs = Date.now()): boolean {
  return !c || (c.exp !== undefined && c.exp * 1000 <= nowMs);
}
