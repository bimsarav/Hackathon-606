import { describe, expect, it } from 'vitest';
import { decodeToken, isExpired } from '../lib/jwt';
import { hasRole, NAV } from '../lib/roles';

function token(payload: object): string {
  const b64 = (o: object) => btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify(o)))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  return `${b64({ alg: 'RS256' })}.${b64(payload)}.sig`;
}

describe('jwt', () => {
  it('decodes the platform claims', () => {
    const c = decodeToken(token({ sub: '42', cid: 1, roles: ['EMPLOYEE', 'ADMIN'], teams: [3], name: 'Emily Jones', email: 'e@x.test', exp: 4102444800 }));
    expect(c).toMatchObject({ sub: '42', cid: 1, roles: ['EMPLOYEE', 'ADMIN'], teams: [3], name: 'Emily Jones' });
    expect(isExpired(c)).toBe(false);
  });
  it('handles unicode names', () => {
    expect(decodeToken(token({ sub: '1', name: 'Zoë Ålund', roles: [] }))?.name).toBe('Zoë Ålund');
  });
  it('rejects malformed tokens', () => {
    expect(decodeToken('abc')).toBeNull();
    expect(decodeToken(null)).toBeNull();
    expect(decodeToken('a.%%%.c')).toBeNull();
  });
  it('detects expiry', () => {
    expect(isExpired(decodeToken(token({ sub: '1', roles: [], exp: 1 })))).toBe(true);
  });
});

describe('role based navigation', () => {
  const visible = (roles: string[]) => NAV.filter((n) => n.show({ sub: '1', roles, teams: [], name: '', email: '' })).map((n) => n.label);
  it('hides admin, audit and reports from employees', () => {
    const v = visible(['EMPLOYEE']);
    expect(v).not.toContain('Admin');
    expect(v).not.toContain('Audit');
    expect(v).not.toContain('Reports');
    expect(v).toContain('Incidents');
  });
  it('shows admin and audit to admins, audit to auditors only', () => {
    expect(visible(['ADMIN'])).toEqual(expect.arrayContaining(['Admin', 'Audit', 'Reports']));
    const a = visible(['AUDITOR']);
    expect(a).toContain('Audit');
    expect(a).not.toContain('Admin');
  });
  it('hasRole matches any listed role', () => {
    expect(hasRole({ roles: ['TECHNICIAN'] }, 'ADMIN', 'TECHNICIAN')).toBe(true);
    expect(hasRole(null, 'ADMIN')).toBe(false);
  });
});
