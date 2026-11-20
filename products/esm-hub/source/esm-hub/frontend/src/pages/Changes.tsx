import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useUser } from '../lib/auth';
import { hasRole, CHANGE_AUTHOR_ROLES } from '../lib/roles';
import { fmtDate, fromLocalInput, human, toLocalInput } from '../lib/format';
import { useNames, useReference } from '../lib/hooks';
import type { CalendarEntry, Change, Page } from '../lib/types';
import { useToast } from '../components/Toast';
import { Badge, Card, Empty, ErrorBox, Input, Loading, PageHead, Pager, Select, StatusBadge, Table, Textarea } from '../components/ui';

const STATUSES = ['DRAFT', 'ASSESSMENT', 'APPROVAL', 'APPROVED', 'IMPLEMENTING', 'IMPLEMENTED', 'FAILED', 'CLOSED', 'CANCELLED', 'REJECTED'];
const TYPES = ['STANDARD', 'NORMAL', 'EMERGENCY'];
const LEVELS = ['LOW', 'MEDIUM', 'HIGH'];
const SETTABLE = ['ASSESSMENT', 'APPROVAL', 'IMPLEMENTING', 'IMPLEMENTED', 'FAILED', 'CLOSED', 'CANCELLED'];

export function ChangeList() {
  const user = useUser();
  const author = hasRole(user, ...CHANGE_AUTHOR_ROLES);
  const [view, setView] = useState('all');
  const [status, setStatus] = useState('');
  const [type, setType] = useState('');
  const [risk, setRisk] = useState('');
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const list = useQuery({ queryKey: ['changes', view, status, type, risk, q, page], queryFn: () => api<Page<Change>>('/changes', { query: { view, status, type, risk, q, page, size: 25 } }) });
  const reset = <T,>(f: (v: T) => void) => (v: T) => { f(v); setPage(1); };
  return (
    <>
      <PageHead title="Changes">
        <Link to="/changes/calendar" className="btn">Calendar</Link>
        {author && <Link to="/changes/new" className="btn primary">New change</Link>}
      </PageHead>
      <form className="filters" role="search" onSubmit={(e) => e.preventDefault()}>
        <Input label="Search" value={q} onChange={(e) => reset(setQ)(e.target.value)} />
        <Select label="View" value={view} onChange={(e) => reset(setView)(e.target.value)} options={[{ value: 'all', label: 'All' }, { value: 'mine', label: 'Mine' }]} />
        <Select label="Status" value={status} onChange={(e) => reset(setStatus)(e.target.value)} blank="Any" options={STATUSES.map((s) => ({ value: s, label: human(s) }))} />
        <Select label="Type" value={type} onChange={(e) => reset(setType)(e.target.value)} blank="Any" options={TYPES.map((s) => ({ value: s, label: human(s) }))} />
        <Select label="Risk" value={risk} onChange={(e) => reset(setRisk)(e.target.value)} blank="Any" options={LEVELS.map((s) => ({ value: s, label: human(s) }))} />
      </form>
      <Loading q={list} />
      <ErrorBox error={list.error} />
      {list.data?.items.length === 0 && <Empty>No changes found.</Empty>}
      {!!list.data?.items.length && (
        <Table caption="Changes">
          <thead><tr><th>Change</th><th>Title</th><th>Type</th><th>Status</th><th>Risk</th><th>Planned start</th></tr></thead>
          <tbody>
            {list.data.items.map((c) => (
              <tr key={c.changeId}>
                <td><Link to={`/changes/${c.changeId}`}>{c.changeNo}</Link></td><td>{c.title}</td>
                <td><StatusBadge value={c.changeType} /></td><td><StatusBadge value={c.status} /></td>
                <td><StatusBadge value={c.riskLevel} /></td><td>{fmtDate(c.plannedStart)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <Pager page={page} onPage={setPage} data={list.data} />
    </>
  );
}

function ChangeForm({ initial, onSaved, submitLabel, mode }: { initial?: Change; onSaved: (c: Change) => void; submitLabel: string; mode: 'create' | 'edit' }) {
  const ref = useReference();
  const toast = useToast();
  const [f, setF] = useState({
    title: initial?.title ?? '', description: initial?.description ?? '', changeType: initial?.changeType ?? 'NORMAL',
    riskLevel: initial?.riskLevel ?? 'MEDIUM', impact: initial?.impact ?? 'MEDIUM', ownerTeamId: String(initial?.ownerTeamId ?? ''),
    plannedStart: toLocalInput(initial?.plannedStart), plannedEnd: toLocalInput(initial?.plannedEnd), rollbackPlan: initial?.rollbackPlan ?? '',
  });
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const m = useMutation({
    mutationFn: () => api<Change>(mode === 'create' ? '/changes' : `/changes/${initial!.changeId}`, {
      method: mode === 'create' ? 'POST' : 'PUT',
      body: {
        title: f.title, description: f.description, changeType: f.changeType, riskLevel: f.riskLevel, impact: f.impact,
        ownerTeamId: f.ownerTeamId ? Number(f.ownerTeamId) : undefined,
        plannedStart: fromLocalInput(f.plannedStart), plannedEnd: fromLocalInput(f.plannedEnd), rollbackPlan: f.rollbackPlan || undefined,
      },
    }),
    onSuccess: (c) => { toast.ok(`Change ${c.changeNo} saved.`); onSaved(c); },
  });
  return (
    <form className="form" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <ErrorBox error={m.error} />
      <Input label="Title" required maxLength={200} value={f.title} onChange={set('title')} />
      <Textarea label="Description" required rows={5} value={f.description} onChange={set('description')} />
      <Select label="Type" value={f.changeType} onChange={set('changeType')} options={TYPES.map((s) => ({ value: s, label: human(s) }))} />
      <Select label="Risk level" value={f.riskLevel} onChange={set('riskLevel')} options={LEVELS.map((s) => ({ value: s, label: human(s) }))} />
      <Select label="Impact" value={f.impact} onChange={set('impact')} options={LEVELS.map((s) => ({ value: s, label: human(s) }))} />
      <Select label="Owner team" value={f.ownerTeamId} onChange={set('ownerTeamId')} blank="Select a team" options={(ref.data?.teams ?? []).map((t) => ({ value: t.teamId, label: t.name }))} />
      <Input label="Planned start" type="datetime-local" value={f.plannedStart} onChange={set('plannedStart')} />
      <Input label="Planned end" type="datetime-local" value={f.plannedEnd} onChange={set('plannedEnd')} />
      <Textarea label="Rollback plan" rows={3} value={f.rollbackPlan} onChange={set('rollbackPlan')} />
      <button type="submit" className="primary" disabled={m.isPending}>{submitLabel}</button>
    </form>
  );
}

export function ChangeNew() {
  const nav = useNavigate();
  return (
    <>
      <PageHead title="New change" />
      <Card><ChangeForm mode="create" submitLabel="Create change" onSaved={(c) => nav(`/changes/${c.changeId}`)} /></Card>
    </>
  );
}

export function ChangeDetail() {
  const { id } = useParams();
  const qc = useQueryClient();
  const toast = useToast();
  const names = useNames();
  const q = useQuery({ queryKey: ['change', id], queryFn: () => api<Change>(`/changes/${id}`), enabled: id !== 'new' });
  const [status, setStatus] = useState('');
  const [editing, setEditing] = useState(false);
  const setSt = useMutation({
    mutationFn: () => api(`/changes/${id}/status`, { body: { status } }),
    onSuccess: () => { toast.ok('Change status updated.'); setStatus(''); void qc.invalidateQueries({ queryKey: ['change', id] }); void qc.invalidateQueries({ queryKey: ['changes'] }); },
  });
  if (id === 'new') return <ChangeNew />;
  const c = q.data;
  if (q.isLoading) return <Loading />;
  if (!c) return <ErrorBox error={q.error} />;
  return (
    <>
      <PageHead title={`${c.changeNo}: ${c.title}`}><Link to="/changes" className="btn">Back to list</Link></PageHead>
      <ErrorBox error={setSt.error} />
      <Card title="Details">
        <dl className="kv">
          <dt>Status</dt><dd data-testid="change-status"><StatusBadge value={c.status} /></dd>
          <dt>Type</dt><dd><StatusBadge value={c.changeType} /></dd>
          <dt>Risk / impact</dt><dd>{human(c.riskLevel)} / {human(c.impact)}</dd>
          <dt>Requester</dt><dd>{c.requesterName ?? c.requesterId}</dd>
          <dt>Owner team</dt><dd>{names.team(c.ownerTeamId)}</dd>
          <dt>Planned</dt><dd>{fmtDate(c.plannedStart)} to {fmtDate(c.plannedEnd)}</dd>
          <dt>Actual</dt><dd>{fmtDate(c.actualStart)} to {fmtDate(c.actualEnd)}</dd>
        </dl>
        {c.planLocked && <p><Badge tone="warn">Plan locked</Badge></p>}
        <h3>Description</h3><p className="pre">{c.description}</p>
        <h3>Rollback plan</h3><p className="pre">{c.rollbackPlan ?? '-'}</p>
        {!c.assessmentComplete && c.missingAssessment && c.missingAssessment.length > 0 && (
          <p role="note" className="warn-box">Assessment incomplete. Missing: {c.missingAssessment.join(', ')}</p>
        )}
        {(c.canEdit || c.canImplement) && (
          <form className="filters" onSubmit={(e) => { e.preventDefault(); setSt.mutate(); }}>
            <Select label="Move to status" value={status} onChange={(e) => setStatus(e.target.value)} blank="Select a status" options={SETTABLE.map((s) => ({ value: s, label: human(s) }))} />
            <button type="submit" className="primary" disabled={!status || setSt.isPending}>Update status</button>
          </form>
        )}
        {c.canEdit && !c.planLocked && <button type="button" onClick={() => setEditing(!editing)} aria-expanded={editing}>Edit change</button>}
      </Card>
      {editing && <Card title="Edit change"><ChangeForm mode="edit" initial={c} submitLabel="Save changes" onSaved={() => { setEditing(false); void qc.invalidateQueries({ queryKey: ['change', id] }); }} /></Card>}
      <Card title="Approval chain">
        {(c.approvals ?? []).length === 0 && <Empty>No approvals required (yet).</Empty>}
        <ol className="timeline">
          {(c.approvals ?? []).map((a) => (
            <li key={a.approvalId}>
              Step {a.stepOrder}: {a.approverRole ? human(a.approverRole) : `User ${a.approverId}`} - <StatusBadge value={a.decision ?? 'PENDING'} />
              {a.comments && <p className="pre">{a.comments}</p>}
              {a.decidedAt && <small className="muted"> {fmtDate(a.decidedAt)}</small>}
            </li>
          ))}
        </ol>
      </Card>
    </>
  );
}

export function ChangeCalendar() {
  const names = useNames();
  const [from, setFrom] = useState(() => { const d = new Date(); d.setDate(d.getDate() - 7); return d.toISOString().slice(0, 10); });
  const [to, setTo] = useState(() => { const d = new Date(); d.setDate(d.getDate() + 60); return d.toISOString().slice(0, 10); });
  const q = useQuery({
    queryKey: ['change-calendar', from, to],
    queryFn: () => api<CalendarEntry[]>('/changes-calendar', { query: { from: new Date(`${from}T00:00:00`).toISOString(), to: new Date(`${to}T23:59:59`).toISOString() } }),
  });
  const byDay = new Map<string, CalendarEntry[]>();
  (q.data ?? []).forEach((e) => {
    const day = e.plannedStart ? e.plannedStart.slice(0, 10) : 'Unscheduled';
    byDay.set(day, [...(byDay.get(day) ?? []), e]);
  });
  const days = [...byDay.keys()].sort();
  return (
    <>
      <PageHead title="Change calendar"><Link to="/changes" className="btn">Back to changes</Link></PageHead>
      <form className="filters" onSubmit={(e) => e.preventDefault()}>
        <Input label="From" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        <Input label="To" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
      </form>
      <Loading q={q} />
      <ErrorBox error={q.error} />
      {days.length === 0 && !q.isLoading && <Empty>No changes are scheduled in this window.</Empty>}
      {days.map((d) => (
        <Card key={d} title={d === 'Unscheduled' ? d : new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { weekday: 'long', dateStyle: 'medium' })}>
          <ul className="list">
            {byDay.get(d)!.map((e) => (
              <li key={e.changeId}>
                <div>
                  <Link to={`/changes/${e.changeId}`}>{e.changeNo}</Link> {e.title}<br />
                  <small className="muted">{fmtDate(e.plannedStart)} - {fmtDate(e.plannedEnd)} - {names.team(e.ownerTeamId)}</small>
                  {e.collidesWith && e.collidesWith.length > 0 && <> <Badge tone="danger">Collides with {e.collidesWith.length} other change(s)</Badge></>}
                </div>
                <div><StatusBadge value={e.changeType} /> <StatusBadge value={e.status} /></div>
              </li>
            ))}
          </ul>
        </Card>
      ))}
    </>
  );
}
