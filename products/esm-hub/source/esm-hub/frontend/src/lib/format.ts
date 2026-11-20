export function fmtDate(s?: string | null): string {
  if (!s) return '-';
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? s : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}
export function fmtDay(s?: string | null): string {
  if (!s) return '-';
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? s : d.toLocaleDateString(undefined, { dateStyle: 'medium' });
}
export function human(s?: string | null): string {
  return s ? s.replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase()) : '-';
}
export function money(n?: number | null): string {
  return n === undefined || n === null ? '-' : n.toLocaleString(undefined, { style: 'currency', currency: 'USD' });
}
/** ISO instant to the value format of a datetime-local input, and back. */
export function toLocalInput(s?: string): string {
  if (!s) return '';
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return '';
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}
export function fromLocalInput(s: string): string | undefined {
  if (!s) return undefined;
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
}
export function slaState(due?: string, breached?: boolean, paused?: boolean, done?: boolean): { label: string; tone: string } {
  if (paused) return { label: 'Paused', tone: 'muted' };
  if (breached) return { label: 'Breached', tone: 'danger' };
  if (!due) return { label: 'No target', tone: 'muted' };
  if (done) return { label: 'Met', tone: 'ok' };
  const left = new Date(due).getTime() - Date.now();
  if (left < 0) return { label: 'Overdue', tone: 'danger' };
  if (left < 3600_000) return { label: 'Due < 1h', tone: 'warn' };
  return { label: 'On track', tone: 'ok' };
}
