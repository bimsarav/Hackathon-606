import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useUser } from '../lib/auth';
import { hasRole, STAFF_ROLES, R } from '../lib/roles';
import { fmtDate, human } from '../lib/format';
import { useNames, useReference } from '../lib/hooks';
import type { Page, Problem } from '../lib/types';
import { useToast } from '../components/Toast';
import { Badge, Card, Empty, ErrorBox, Input, Loading, PageHead, Pager, Select, StatusBadge, Table, Textarea } from '../components/ui';

const STATUSES = ['OPEN', 'INVESTIGATING', 'KNOWN_ERROR', 'RESOLVED', 'CLOSED'];

export function ProblemList() {
  const user = useUser();
  const canCreate = hasRole(user, ...STAFF_ROLES);
  const qc = useQueryClient();
  const toast = useToast();
  const ref = useReference();
  const [status, setStatus] = useState('');
  const [known, setKnown] = useState(false);
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [show, setShow] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [teamId, setTeamId] = useState('');
  const list = useQuery({
    queryKey: ['problems', status, known, q, page],
    queryFn: () => api<Page<Problem>>('/problems', { query: { status, knownError: known || undefined, q, page, size: 25 } }),
  });
  const create = useMutation({
    mutationFn: () => api<Problem>('/problems', { body: { title, description, ownerTeamId: teamId ? Number(teamId) : undefined } }),
    onSuccess: (p) => { toast.ok(`Problem ${p.problemNo} created.`); setShow(false); setTitle(''); setDescription(''); void qc.invalidateQueries({ queryKey: ['problems'] }); },
  });
  return (
    <>
      <PageHead title="Problems">
        {canCreate && <button type="button" className="primary" onClick={() => setShow(!show)} aria-expanded={show}>New problem</button>}
      </PageHead>
      {show && (
        <Card title="New problem">
          <form className="form" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
            <ErrorBox error={create.error} />
            <Input label="Title" required minLength={3} value={title} onChange={(e) => setTitle(e.target.value)} />
            <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
            <Select label="Owner team" value={teamId} onChange={(e) => setTeamId(e.target.value)} blank="None" options={(ref.data?.teams ?? []).map((t) => ({ value: t.teamId, label: t.name }))} />
            <button type="submit" className="primary" disabled={create.isPending}>Create problem</button>
          </form>
        </Card>
      )}
      <form className="filters" role="search" onSubmit={(e) => e.preventDefault()}>
        <Input label="Search" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <Select label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} blank="Any" options={STATUSES.map((s) => ({ value: s, label: human(s) }))} />
        <label className="inline"><input type="checkbox" checked={known} onChange={(e) => { setKnown(e.target.checked); setPage(1); }} /> Known errors only</label>
      </form>
      <Loading q={list} />
      <ErrorBox error={list.error} />
      {list.data?.items.length === 0 && <Empty>No problems found.</Empty>}
      {!!list.data?.items.length && (
        <Table caption="Problems">
          <thead><tr><th>Problem</th><th>Title</th><th>Status</th><th>Incidents</th><th>Updated</th></tr></thead>
          <tbody>
            {list.data.items.map((p) => (
              <tr key={p.id}>
                <td><Link to={`/problems/${p.id}`}>{p.problemNo}</Link></td>
                <td>{p.title} {p.knownError && <Badge tone="danger">Known error</Badge>}</td>
                <td><StatusBadge value={p.status} /></td>
                <td>{p.incidentCount}</td>
                <td>{fmtDate(p.updatedAt ?? p.createdAt)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <Pager page={page} onPage={setPage} data={list.data} />
    </>
  );
}

export function ProblemDetail() {
  const { id } = useParams();
  const user = useUser();
  const canEdit = hasRole(user, ...STAFF_ROLES, R.ADMIN);
  const qc = useQueryClient();
  const toast = useToast();
  const names = useNames();
  const q = useQuery({ queryKey: ['problem', id], queryFn: () => api<Problem>(`/problems/${id}`) });
  const p = q.data;
  const [status, setStatus] = useState('');
  const [rootCause, setRootCause] = useState('');
  const [workaround, setWorkaround] = useState('');
  const [loaded, setLoaded] = useState<number | null>(null);
  if (p && loaded !== p.id) { setLoaded(p.id); setStatus(p.status); setRootCause(p.rootCause ?? ''); setWorkaround(p.workaround ?? ''); }
  const [incidentId, setIncidentId] = useState('');
  const refresh = () => { void qc.invalidateQueries({ queryKey: ['problem', id] }); void qc.invalidateQueries({ queryKey: ['problems'] }); };
  const update = useMutation({
    mutationFn: () => api(`/problems/${id}`, { method: 'PATCH', body: { status, rootCause, workaround } }),
    onSuccess: () => { toast.ok('Problem updated.'); refresh(); },
  });
  const link = useMutation({
    mutationFn: () => api(`/problems/${id}/incidents`, { body: { incidentIds: [Number(incidentId)] } }),
    onSuccess: () => { toast.ok('Incident linked.'); setIncidentId(''); refresh(); },
  });
  const unlink = useMutation({
    mutationFn: (iid: number) => api(`/problems/${id}/incidents/${iid}`, { method: 'DELETE' }),
    onSuccess: () => { toast.ok('Incident unlinked.'); refresh(); },
  });
  if (q.isLoading) return <Loading />;
  if (!p) return <ErrorBox error={q.error} />;
  return (
    <>
      <PageHead title={`${p.problemNo}: ${p.title}`}><Link to="/problems" className="btn">Back to list</Link></PageHead>
      <ErrorBox error={update.error ?? link.error ?? unlink.error} />
      <Card title="Details">
        <dl className="kv">
          <dt>Status</dt><dd><StatusBadge value={p.status} /></dd>
          <dt>Owner team</dt><dd>{names.team(p.ownerTeamId)}</dd>
          <dt>Created</dt><dd>{fmtDate(p.createdAt)}</dd>
        </dl>
        <p className="pre">{p.description}</p>
        {canEdit ? (
          <form className="form" onSubmit={(e) => { e.preventDefault(); update.mutate(); }}>
            <Select label="Status" value={status} onChange={(e) => setStatus(e.target.value)} options={STATUSES.map((s) => ({ value: s, label: human(s) }))} />
            <Textarea label="Root cause" value={rootCause} onChange={(e) => setRootCause(e.target.value)} />
            <Textarea label="Workaround" value={workaround} onChange={(e) => setWorkaround(e.target.value)} />
            <button type="submit" className="primary" disabled={update.isPending}>Save problem</button>
          </form>
        ) : (
          <dl className="kv"><dt>Root cause</dt><dd>{p.rootCause ?? '-'}</dd><dt>Workaround</dt><dd>{p.workaround ?? '-'}</dd></dl>
        )}
      </Card>
      <Card title="Linked incidents">
        {(p.incidents ?? []).length === 0 && <Empty>No incidents linked.</Empty>}
        <ul className="list">
          {(p.incidents ?? []).map((i) => (
            <li key={i.id}>
              <div><Link to={`/incidents/${i.id}`}>{i.ticketNo}</Link> {i.title} <StatusBadge value={i.status} /></div>
              {canEdit && <button type="button" onClick={() => unlink.mutate(i.id)}>Unlink</button>}
            </li>
          ))}
        </ul>
        {canEdit && (
          <form className="filters" onSubmit={(e) => { e.preventDefault(); link.mutate(); }}>
            <Input label="Incident ID to link" type="number" min={1} required value={incidentId} onChange={(e) => setIncidentId(e.target.value)} />
            <button type="submit" disabled={link.isPending}>Link incident</button>
          </form>
        )}
      </Card>
    </>
  );
}
