// Display helpers. All operational times are UTC (airline convention "Z").

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2026-11-21T13:55:00" → "21 Nov 13:55Z" (the API sends naive UTC timestamps). */
export function utc(value: string | null | undefined): string {
  if (!value) return "—";
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(value);
  if (!m) return value;
  return `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[4]}:${m[5]}Z`;
}

export function hhmm(value: string | null | undefined): string {
  if (!value) return "—";
  const m = /[T ](\d{2}):(\d{2})/.exec(value);
  return m ? `${m[1]}:${m[2]}` : value;
}

export const aed = (n: number): string => `AED ${Math.round(n).toLocaleString("en-US")}`;
export const num = (n: number): string => n.toLocaleString("en-US");

export function minutes(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  if (n < 60) return `${n} min`;
  const h = Math.floor(n / 60);
  const m = n % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}
