import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, newKey } from '../lib/api';
import { useUser } from '../lib/auth';
import { hasRole, CONFIG_ROLES } from '../lib/roles';
import { fmtDate, human, money } from '../lib/format';
import { useNames, useReference } from '../lib/hooks';
import type { CatalogueItem, Page, ServiceRequest } from '../lib/types';
import { useToast } from '../components/Toast';
import { Badge, Card, Empty, ErrorBox, Input, Loading, PageHead, Pager, Select, StatusBadge, Table, Textarea } from '../components/ui';

export function Catalogue() {
  const user = useUser();
  const manage = hasRole(user, ...CONFIG_ROLES);
  const nav = useNavigate();
  const toast = useToast();
  const qc = useQueryClient();
  const ref = useReference();
  const q = useQuery({ queryKey: ['catalogue'], queryFn: () => api<CatalogueItem[]>('/catalogue') });
  const [item, setItem] = useState<CatalogueItem | null>(null);
  const [title, setTitle] = useState('');
  const [details, setDetails] = useState('');
  const [cost, setCost] = useState('');
  const [key, setKey] = useState(newKey);
  const submit = useMutation({
    mutationFn: () => api<ServiceRequest>('/requests', {
      idempotencyKey: key,
      body: { itemId: item!.itemId, title: title || item!.name, details, estimatedCost: cost ? Number(cost) : item!.baseCost ?? undefined },
    }),
    onSuccess: (r) => { toast.ok(`Request ${r.requestNo} submitted.`); setItem(null); setKey(newKey()); nav(`/requests/${r.requestId}`); },
  });

  const [showNew, setShowNew] = useState(false);
  const [nName, setNName] = useState('');
  const [nDesc, setNDesc] = useState('');
  const [nSvc, setNSvc] = useState('');
  const [nCost, setNCost] = useState('0');
  const [nTeam, setNTeam] = useState('');
  const [nMgr, setNMgr] = useState(true);
  const create = useMutation({
    mutationFn: () => api('/catalogue', {
      body: {
        serviceId: Number(nSvc), name: nName, description: nDesc, baseCost: Number(nCost) || 0,
        fulfilmentTeamId: nTeam ? Number(nTeam) : undefined, active: true,
        steps: nMgr ? [{ stepOrder: 1, approverType: 'MANAGER' }] : [],
      },
    }),
    onSuccess: () => { toast.ok('Catalogue item created.'); setShowNew(false); setNName(''); void qc.invalidateQueries({ queryKey: ['catalogue'] }); },
  });

  return (
    <>
      <PageHead title="Service catalogue">
        <Link to="/requests" className="btn">My requests</Link>
        {manage && <button type="button" onClick={() => setShowNew(!showNew)} aria-expanded={showNew}>New item</button>}
      </PageHead>
      <Loading q={q} />
      <ErrorBox error={q.error} />
      {manage && showNew && (
        <Card title="New catalogue item">
          <form className="form" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
            <ErrorBox error={create.error} />
            <Select label="Service" required value={nSvc} onChange={(e) => setNSvc(e.target.value)} blank="Select a service" options={(ref.data?.services ?? []).map((s) => ({ value: s.serviceId, label: s.name }))} />
            <Input label="Name" required minLength={3} value={nName} onChange={(e) => setNName(e.target.value)} />
            <Textarea label="Description" value={nDesc} onChange={(e) => setNDesc(e.target.value)} />
            <Input label="Base cost" type="number" min={0} step="0.01" value={nCost} onChange={(e) => setNCost(e.target.value)} />
            <Select label="Fulfilment team" value={nTeam} onChange={(e) => setNTeam(e.target.value)} blank="None" options={(ref.data?.teams ?? []).map((t) => ({ value: t.teamId, label: t.name }))} />
            <label className="inline"><input type="checkbox" checked={nMgr} onChange={(e) => setNMgr(e.target.checked)} /> Requires manager approval</label>
            <button type="submit" className="primary" disabled={create.isPending}>Create item</button>
          </form>
        </Card>
      )}
      {item && (
        <Card title={`Request: ${item.name}`}>
          <form className="form" aria-label={`Request ${item.name}`} onSubmit={(e) => { e.preventDefault(); submit.mutate(); }}>
            <ErrorBox error={submit.error} />
            <Input label="Request title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder={item.name} />
            <Textarea label="Details" value={details} onChange={(e) => setDetails(e.target.value)} />
            <Input label="Estimated cost" type="number" min={0} step="0.01" value={cost} onChange={(e) => setCost(e.target.value)} placeholder={String(item.baseCost ?? 0)} />
            {item.steps && item.steps.length > 0 && <p className="muted">Approval steps: {item.steps.map((s) => (s.approverType === 'MANAGER' ? 'Manager' : human(s.approverRole))).join(' then ')}</p>}
            <div className="actions">
              <button type="submit" className="primary" disabled={submit.isPending}>Submit request</button>
              <button type="button" onClick={() => setItem(null)}>Cancel</button>
            </div>
          </form>
        </Card>
      )}
      <div className="cards">
        {q.data?.map((c) => (
          <article key={c.itemId} className="card item">
            <h2>{c.name}</h2>
            <p className="muted">{c.serviceName}</p>
            <p>{c.description}</p>
            <p>{money(c.baseCost)} {!c.active && <Badge tone="muted">Inactive</Badge>}</p>
            <button type="button" onClick={() => { setItem(c); setTitle(''); setDetails(''); setCost(''); }} disabled={!c.active}>Request this</button>
          </article>
        ))}
      </div>
      {q.data?.length === 0 && <Empty>The catalogue is empty.</Empty>}
    </>
  );
}

const REQ_STATUSES = ['SUBMITTED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'IN_PROGRESS', 'FULFILLED', 'CANCELLED'];

export function RequestList() {
  const user = useUser();
  const wide = hasRole(user, 'SERVICE_DESK_AGENT', 'TEAM_LEAD', 'SERVICE_MANAGER', 'AUDITOR', 'ADMIN', 'TECHNICIAN');
  const [view, setView] = useState('mine');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const q = useQuery({ queryKey: ['requests', view, status, page], queryFn: () => api<Page<ServiceRequest>>('/requests', { query: { view, status, page, size: 25 } }) });
  return (
    <>
      <PageHead title="Requests"><Link to="/catalogue" className="btn primary">Browse catalogue</Link></PageHead>
      <form className="filters" onSubmit={(e) => e.preventDefault()}>
        {wide && <Select label="View" value={view} onChange={(e) => { setView(e.target.value); setPage(1); }} options={[{ value: 'mine', label: 'My requests' }, { value: 'fulfilment', label: 'Fulfilment queue' }, { value: 'all', label: 'All' }]} />}
        <Select label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} blank="Any" options={REQ_STATUSES.map((s) => ({ value: s, label: human(s) }))} />
      </form>
      <Loading q={q} />
      <ErrorBox error={q.error} />
      {q.data?.items.length === 0 && <Empty>No requests.</Empty>}
      {!!q.data?.items.length && (
        <Table caption="Service requests">
          <thead><tr><th>Request</th><th>Title</th><th>Status</th><th>Requester</th><th>Cost</th><th>Requested</th></tr></thead>
          <tbody>
            {q.data.items.map((r) => (
              <tr key={r.requestId}>
                <td><Link to={`/requests/${r.requestId}`}>{r.requestNo}</Link></td>
                <td>{r.title}</td><td><StatusBadge value={r.status} /></td><td>{r.requesterName ?? r.requesterId}</td>
                <td>{money(r.estimatedCost)}</td><td>{fmtDate(r.requestedAt)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <Pager page={page} onPage={setPage} data={q.data} />
    </>
  );
}

export function RequestDetail() {
  const { id } = useParams();
  const qc = useQueryClient();
  const toast = useToast();
  const names = useNames();
  const q = useQuery({ queryKey: ['request', id], queryFn: () => api<ServiceRequest>(`/requests/${id}`) });
  const act = useMutation({
    mutationFn: (status: string) => api(`/requests/${id}/status`, { body: { status } }),
    onSuccess: () => { toast.ok('Request updated.'); void qc.invalidateQueries({ queryKey: ['request', id] }); void qc.invalidateQueries({ queryKey: ['requests'] }); },
  });
  const r = q.data;
  if (q.isLoading) return <Loading />;
  if (!r) return <ErrorBox error={q.error} />;
  const open = ['SUBMITTED', 'PENDING_APPROVAL', 'APPROVED', 'IN_PROGRESS'].includes(r.status);
  return (
    <>
      <PageHead title={`${r.requestNo}: ${r.title}`}><Link to="/requests" className="btn">Back to list</Link></PageHead>
      <ErrorBox error={act.error} />
      <Card title="Details">
        <dl className="kv">
          <dt>Status</dt><dd data-testid="request-status"><StatusBadge value={r.status} /></dd>
          <dt>Requester</dt><dd>{r.requesterName ?? r.requesterId}</dd>
          <dt>Service</dt><dd>{names.service(r.serviceId)}</dd>
          <dt>Estimated cost</dt><dd>{money(r.estimatedCost)}</dd>
          <dt>Requested</dt><dd>{fmtDate(r.requestedAt)}</dd>
          <dt>Approved</dt><dd>{fmtDate(r.approvedAt)}</dd>
          <dt>Fulfilled</dt><dd>{fmtDate(r.fulfilledAt)}</dd>
        </dl>
        <p className="pre">{r.details}</p>
        <div className="actions">
          {r.canFulfil && r.status === 'APPROVED' && <button type="button" onClick={() => act.mutate('IN_PROGRESS')}>Start work</button>}
          {r.canFulfil && (r.status === 'IN_PROGRESS' || r.status === 'APPROVED') && <button type="button" className="primary" onClick={() => act.mutate('FULFILLED')}>Mark fulfilled</button>}
          {open && <button type="button" onClick={() => act.mutate('CANCELLED')}>Cancel request</button>}
        </div>
      </Card>
      <Card title="Approval chain">
        {(r.approvals ?? []).length === 0 && <Empty>No approval needed.</Empty>}
        <ol className="timeline">
          {(r.approvals ?? []).map((a) => (
            <li key={a.approvalId}>
              Step {a.stepOrder}: {a.approverRole ? human(a.approverRole) : 'Manager'} - <StatusBadge value={a.decision ?? 'PENDING'} />
              {a.comments && <p className="pre">{a.comments}</p>}
              {a.decidedAt && <small className="muted"> {fmtDate(a.decidedAt)}</small>}
            </li>
          ))}
        </ol>
      </Card>
    </>
  );
}
