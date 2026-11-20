import { useId, type ReactNode, type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';
import { ApiError } from '../lib/api';
import { human } from '../lib/format';
import type { Page } from '../lib/types';

export function ErrorBox({ error }: { error: unknown }) {
  if (!error) return null;
  const e = error instanceof ApiError ? error : null;
  const fields = e && Array.isArray(e.problem.errors) ? (e.problem.errors as unknown[]) : [];
  return (
    <div className="error" role="alert">
      <strong>{e?.problem.title ?? 'Error'}</strong>
      <div>{e ? e.problem.detail ?? e.message : (error as Error).message}</div>
      {fields.length > 0 && (
        <ul>{fields.map((f, i) => <li key={i}>{typeof f === 'string' ? f : JSON.stringify(f)}</li>)}</ul>
      )}
      {e?.problem.requestId && <small>Request ID: <code>{e.problem.requestId}</code></small>}
    </div>
  );
}

export function Loading({ q }: { q?: { isLoading: boolean } }) {
  if (q && !q.isLoading) return null;
  return <p className="muted" role="status">Loading...</p>;
}

export function Empty({ children = 'Nothing to show.' }: { children?: ReactNode }) {
  return <p className="muted empty">{children}</p>;
}

export function Badge({ tone, children }: { tone?: string; children: ReactNode }) {
  return <span className={`badge badge-${tone ?? 'neutral'}`}>{children}</span>;
}

const TONES: Record<string, string> = {
  NEW: 'info', ASSIGNED: 'info', IN_PROGRESS: 'warn', PENDING_USER: 'muted', RESOLVED: 'ok', CLOSED: 'muted', CANCELLED: 'muted',
  SUBMITTED: 'info', PENDING_APPROVAL: 'warn', APPROVED: 'ok', REJECTED: 'danger', FULFILLED: 'ok',
  OPEN: 'info', INVESTIGATING: 'warn', KNOWN_ERROR: 'danger', DRAFT: 'muted', UNDER_REVIEW: 'warn', PUBLISHED: 'ok', RETIRED: 'muted',
  ASSESSMENT: 'info', APPROVAL: 'warn', IMPLEMENTING: 'warn', IMPLEMENTED: 'ok', FAILED: 'danger',
  IN_STOCK: 'ok', REPAIR: 'warn', LOST: 'danger', P1: 'danger', P2: 'warn', Critical: 'danger', High: 'warn',
  EMERGENCY: 'danger', HIGH: 'danger', MEDIUM: 'warn', LOW: 'ok',
};
export function StatusBadge({ value }: { value?: string | null }) {
  if (!value) return <span>-</span>;
  return <Badge tone={TONES[value]}>{human(value)}</Badge>;
}

interface FieldProps { label: string; hint?: string; children: (id: string) => ReactNode }
export function Field({ label, hint, children }: FieldProps) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children(id)}
      {hint && <small className="muted">{hint}</small>}
    </div>
  );
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string };
export function Input({ label, hint, ...rest }: InputProps) {
  return <Field label={label} hint={hint}>{(id) => <input id={id} {...rest} />}</Field>;
}
type TextProps = TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; hint?: string };
export function Textarea({ label, hint, ...rest }: TextProps) {
  return <Field label={label} hint={hint}>{(id) => <textarea id={id} rows={4} {...rest} />}</Field>;
}
type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & { label: string; hint?: string; options: { value: string | number; label: string }[]; blank?: string };
export function Select({ label, hint, options, blank, ...rest }: SelectProps) {
  return (
    <Field label={label} hint={hint}>
      {(id) => (
        <select id={id} {...rest}>
          {blank !== undefined && <option value="">{blank}</option>}
          {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      )}
    </Field>
  );
}

export function Pager({ page, onPage, data }: { page: number; onPage: (p: number) => void; data?: Page<unknown> }) {
  if (!data) return null;
  const pages = Math.max(1, Math.ceil(data.total / data.size));
  return (
    <nav className="pager" aria-label="Pagination">
      <button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button>
      <span aria-live="polite">Page {page} of {pages} ({data.total} total)</span>
      <button type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
    </nav>
  );
}

export function Table({ caption, children }: { caption: string; children: ReactNode }) {
  return (
    <div className="table-wrap" tabIndex={0} role="region" aria-label={caption}>
      <table><caption className="sr-only">{caption}</caption>{children}</table>
    </div>
  );
}

export function PageHead({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="page-head"><h1>{title}</h1><div className="actions">{children}</div></div>;
}

export function Card({ title, children, className }: { title?: string; children: ReactNode; className?: string }) {
  return <section className={`card ${className ?? ''}`}>{title && <h2>{title}</h2>}{children}</section>;
}

export function BarChart({ title, rows }: { title: string; rows: { label: string; value: number; extra?: number }[] }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      {rows.length === 0 && <Empty>No data.</Empty>}
      <ul>
        {rows.map((r) => (
          <li key={r.label}>
            <span className="chart-label">{r.label}</span>
            <span className="chart-track" aria-hidden="true">
              <span className="chart-bar" style={{ width: `${(r.value / max) * 100}%` }} />
            </span>
            <span className="chart-value">{r.value}{r.extra ? ` (${r.extra} breached)` : ''}</span>
          </li>
        ))}
      </ul>
    </figure>
  );
}
