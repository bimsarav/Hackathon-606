import type { Claims } from './jwt';

export const R = {
  EMPLOYEE: 'EMPLOYEE', DESK: 'SERVICE_DESK_AGENT', TECH: 'TECHNICIAN', LEAD: 'TEAM_LEAD', SM: 'SERVICE_MANAGER',
  CM: 'CHANGE_MANAGER', AM: 'ASSET_MANAGER', KE: 'KNOWLEDGE_EDITOR', ADMIN: 'ADMIN', AUDITOR: 'AUDITOR',
} as const;

export function hasRole(c: Pick<Claims, 'roles'> | null | undefined, ...roles: string[]): boolean {
  return !!c && roles.some((r) => c.roles.includes(r));
}

export const REPORT_ROLES = [R.LEAD, R.SM, R.AUDITOR, R.ADMIN, R.DESK, R.CM, R.AM];
export const STAFF_ROLES = [R.DESK, R.TECH, R.LEAD, R.SM];
export const WIDE_INCIDENT_ROLES = [R.DESK, R.LEAD, R.SM, R.AUDITOR, R.ADMIN, R.CM];
export const CONFIG_ROLES = [R.SM, R.ADMIN];
export const KB_AUTHOR_ROLES = [R.KE, R.DESK, R.TECH, R.LEAD, R.SM];
export const CHANGE_ROLES = [R.DESK, R.TECH, R.LEAD, R.SM, R.CM, R.AUDITOR, R.ADMIN];
export const CHANGE_AUTHOR_ROLES = [R.TECH, R.LEAD, R.SM, R.CM, R.ADMIN];
export const ASSET_ROLES = [R.AM, R.DESK, R.TECH, R.LEAD, R.SM, R.AUDITOR, R.ADMIN];
export const ASSET_EXPORT_ROLES = [R.AM, R.AUDITOR, R.ADMIN, R.SM];

export interface NavItem { to: string; label: string; show: (c: Claims) => boolean }

export const NAV: NavItem[] = [
  { to: '/', label: 'Dashboard', show: () => true },
  { to: '/incidents', label: 'Incidents', show: () => true },
  { to: '/problems', label: 'Problems', show: (c) => hasRole(c, ...STAFF_ROLES, R.CM, R.AUDITOR, R.ADMIN) },
  { to: '/catalogue', label: 'Catalogue', show: () => true },
  { to: '/requests', label: 'Requests', show: () => true },
  { to: '/approvals', label: 'Approvals', show: () => true },
  { to: '/changes', label: 'Changes', show: (c) => hasRole(c, ...CHANGE_ROLES) },
  { to: '/assets', label: 'Assets', show: () => true },
  { to: '/knowledge', label: 'Knowledge', show: () => true },
  { to: '/notifications', label: 'Notifications', show: () => true },
  { to: '/reports', label: 'Reports', show: (c) => hasRole(c, ...REPORT_ROLES) },
  { to: '/audit', label: 'Audit', show: (c) => hasRole(c, R.AUDITOR, R.ADMIN) },
  { to: '/admin', label: 'Admin', show: (c) => hasRole(c, ...CONFIG_ROLES) },
  { to: '/account', label: 'My account', show: () => true },
];
