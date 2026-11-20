import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api, download, newKey } from '../lib/api';
import { useUser } from '../lib/auth';
import { hasRole, WIDE_INCIDENT_ROLES, R } from '../lib/roles';
import { fmtDate, human, slaState } from '../lib/format';
import { useNames, usePriorities, useReference } from '../lib/hooks';
import type { Incident, Page } from '../lib/types';
import { useToast } from '../components/Toast';
import { Badge, Empty, ErrorBox, Input, Loading, PageHead, Pager, Select, StatusBadge, Table, Textarea, Card } from '../components/ui';

const STATUSES = ['NEW', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_USER', 'RESOLVED', 'CLOSED', 'CANCELLED'];

export function SlaBadge({ i }: { i: Pick<Incident, 'dueAt' | 'resolutionBreached' | 'slaPaused' | 'resolvedAt' | 'closedAt'> }) {
  const s = slaState(i.dueAt, i.resolutionBreached, i.slaPaused, !!(i.resolvedAt || i.closedAt));
  return <Badge tone={s.tone}>{s.label}</Badge>;
}

export function IncidentList() {
  const user = useUser();
  const wide = hasRole(user, ...WIDE_INCIDENT_ROLES);
  const tech = hasRole(user, R.TECH);
  const views = [['mine', 'My incidents']];
  if (tech || wide) views.push(['assigned', 'Assigned to me'], ['queue', 'Team queue']);
  if (wide) views.push(['unassigned', 'Unassigned'], ['open', 'Open'], ['all', 'All']);
  const [sp, setSp] = useSearchParams();
  const view = sp.get('view') ?? 'mine';
  const status = sp.get('status') ?? '';
  const priorityId = sp.get('priorityId') ?? '';
  const teamId = sp.get('teamId') ?? '';
  const q = sp.get('q') ?? '';
  const breached = sp.get('breached') === 'true';
  const [page, setPage] = useState(1);
  const [text, setText] = useState(q);
  const ref = useReference();
  const prios = usePriorities();
  const names = useNames();
  const toast = useToast();
  const set = (k: string, v: string) => {
    const n = new URLSearchParams(sp);
    if (v) n.set(k, v); else n.delete(k);
    setSp(n, { replace: true });
    setPage(1);
  };
  const params = { view, status, priorityId, teamId, q, breached, page, size: 25 };
  const list = useQuery({ queryKey: ['incidents', params], queryFn: () => api<Page<Incident>>('/incidents', { query: params }) });

  return (
    <>
      <PageHead title="Incidents">
        {wide && <button type="button" onClick={() => download('/incidents/export', { q, status, priorityId, teamId, view, breached }, 'incidents.csv').catch((e: Error) => toast.error(e.message))}>Export CSV</button>}
        <Link to="/incidents/new" className="btn primary">New incident</Link>
      </PageHead>
      <div role="tablist" aria-label="Incident views" className="tabs">
        {views.map(([v, label]) => (
          <button key={v} type="button" role="tab" aria-selected={view === v} className={view === v ? 'active' : ''} onClick={() => set('view', v)}>{label}</button>
        ))}
      </div>
      <form className="filters" role="search" onSubmit={(e: FormEvent) => { e.preventDefault(); set('q', text); }}>
        <Input label="Search" value={text} onChange={(e) => setText(e.target.value)} placeholder="Title, ticket no..." />
        <Select label="Status" value={status} onChange={(e) => set('status', e.target.value)} blank="Any" options={STATUSES.map((s) => ({ value: s, label: human(s) }))} />
        <Select label="Priority" value={priorityId} onChange={(e) => set('priorityId', e.target.value)} blank="Any" options={(prios.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />
        {wide && <Select label="Team" value={teamId} onChange={(e) => set('teamId', e.target.value)} blank="Any" options={(ref.data?.teams ?? []).map((t) => ({ value: t.teamId, label: t.name }))} />}
        <label className="inline"><input type="checkbox" checked={breached} onChange={(e) => set('breached', e.target.checked ? 'true' : '')} /> SLA breached</label>
        <button type="submit">Search</button>
      </form>
      <Loading q={list} />
      <ErrorBox error={list.error} />
      {list.data?.items.length === 0 && <Empty>No incidents match.</Empty>}
      {!!list.data?.items.length && (
        <Table caption="Incidents">
          <thead><tr><th>Ticket</th><th>Title</th><th>Status</th><th>Priority</th><th>Team</th><th>Assignee</th><th>SLA</th><th>Created</th></tr></thead>
          <tbody>
            {list.data.items.map((i) => (
              <tr key={i.id}>
                <td><Link to={`/incidents/${i.id}`}>{i.ticketNo}</Link></td>
                <td>{i.title}</td>
                <td><StatusBadge value={i.status} /></td>
                <td>{i.priority}</td>
                <td>{i.teamName ?? names.team(i.assignedTeamId)}</td>
                <td>{i.assigneeName ?? '-'}</td>
                <td><SlaBadge i={i} /></td>
                <td>{fmtDate(i.createdAt)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <Pager page={page} onPage={setPage} data={list.data} />
    </>
  );
}

const CHANNELS = ['PORTAL', 'EMAIL', 'PHONE', 'CHAT', 'MONITORING'];

export function IncidentNew() {
  const user = useUser();
  const desk = hasRole(user, R.DESK, R.LEAD, R.SM);
  const nav = useNavigate();
  const toast = useToast();
  const ref = useReference();
  const prios = usePriorities();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [serviceId, setServiceId] = useState('');
  const [priorityId, setPriorityId] = useState('');
  const [channel, setChannel] = useState('PORTAL');
  const [requesterId, setRequesterId] = useState('');
  const [key] = useState(newKey);
  const m = useMutation({
    mutationFn: () => api<Incident>('/incidents', {
      idempotencyKey: key,
      body: {
        title, description, channel,
        serviceId: serviceId ? Number(serviceId) : undefined,
        priorityId: desk && priorityId ? Number(priorityId) : undefined,
        requesterId: desk && requesterId ? Number(requesterId) : undefined,
      },
    }),
    onSuccess: (i) => { toast.ok(`Incident ${i.ticketNo} created.`); nav(`/incidents/${i.id}`); },
  });
  return (
    <>
      <PageHead title="New incident" />
      <Card>
        <form className="form" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
          <ErrorBox error={m.error} />
          <Input label="Title" required minLength={3} maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />
          <Textarea label="Description" required minLength={3} rows={6} value={description} onChange={(e) => setDescription(e.target.value)} />
          <Select label="Service" value={serviceId} onChange={(e) => setServiceId(e.target.value)} blank="Not sure" options={(ref.data?.services ?? []).filter((s) => s.active).map((s) => ({ value: s.serviceId, label: s.name }))} />
          <Select label="Channel" value={channel} onChange={(e) => setChannel(e.target.value)} options={CHANNELS.map((c) => ({ value: c, label: human(c) }))} />
          {desk && (
            <>
              <Select label="Priority" value={priorityId} onChange={(e) => setPriorityId(e.target.value)} blank="Default" options={(prios.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />
              <Input label="On behalf of (user ID)" type="number" min={1} value={requesterId} onChange={(e) => setRequesterId(e.target.value)} hint="Leave blank to log it for yourself." />
            </>
          )}
          <button type="submit" className="primary" disabled={m.isPending}>Submit incident</button>
        </form>
      </Card>
    </>
  );
}
