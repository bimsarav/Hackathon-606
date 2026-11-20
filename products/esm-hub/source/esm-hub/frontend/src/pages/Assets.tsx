import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, download } from '../lib/api';
import { useUser } from '../lib/auth';
import { hasRole, R, ASSET_EXPORT_ROLES } from '../lib/roles';
import { fmtDate, fmtDay, human, money } from '../lib/format';
import { useNames, useReference } from '../lib/hooks';
import type { Asset, Page, UserView } from '../lib/types';
import { useToast } from '../components/Toast';
import { Badge, Card, Empty, ErrorBox, Input, Loading, PageHead, Pager, Select, StatusBadge, Table } from '../components/ui';

const STATUSES = ['IN_STOCK', 'ASSIGNED', 'REPAIR', 'RETIRED', 'LOST'];

export function AssetList() {
  const user = useUser();
  const manage = hasRole(user, R.AM, R.ADMIN);
  const exporter = hasRole(user, ...ASSET_EXPORT_ROLES);
  const qc = useQueryClient();
  const toast = useToast();
  const ref = useReference();
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [warranty, setWarranty] = useState('');
  const [page, setPage] = useState(1);
  const [show, setShow] = useState(false);
  const [f, setF] = useState({ assetTag: '', assetType: 'Laptop', manufacturer: '', model: '', serialNumber: '', warrantyEnd: '', officeId: '', purchaseCost: '' });
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  const list = useQuery({ queryKey: ['assets', q, status, warranty, page], queryFn: () => api<Page<Asset>>('/assets', { query: { q, status, warranty, page, size: 25 } }) });
  const create = useMutation({
    mutationFn: () => api<Asset>('/assets', {
      body: {
        assetTag: f.assetTag, assetType: f.assetType, manufacturer: f.manufacturer || undefined, model: f.model || undefined,
        serialNumber: f.serialNumber || undefined, warrantyEnd: f.warrantyEnd || undefined,
        officeId: f.officeId ? Number(f.officeId) : undefined, purchaseCost: f.purchaseCost ? Number(f.purchaseCost) : undefined,
      },
    }),
    onSuccess: (a) => { toast.ok(`Asset ${a.assetTag} created.`); setShow(false); void qc.invalidateQueries({ queryKey: ['assets'] }); },
  });
  return (
    <>
      <PageHead title="Assets">
        {exporter && <button type="button" onClick={() => download('/assets/export', { status, warranty }, 'assets.csv').catch((e: Error) => toast.error(e.message))}>Export CSV</button>}
        {manage && <button type="button" className="primary" onClick={() => setShow(!show)} aria-expanded={show}>New asset</button>}
      </PageHead>
      {manage && show && (
        <Card title="New asset">
          <form className="form" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
            <ErrorBox error={create.error} />
            <Input label="Asset tag" required minLength={2} value={f.assetTag} onChange={set('assetTag')} />
            <Input label="Type" required value={f.assetType} onChange={set('assetType')} />
            <Input label="Manufacturer" value={f.manufacturer} onChange={set('manufacturer')} />
            <Input label="Model" value={f.model} onChange={set('model')} />
            <Input label="Serial number" value={f.serialNumber} onChange={set('serialNumber')} />
            <Input label="Warranty end" type="date" value={f.warrantyEnd} onChange={set('warrantyEnd')} />
            <Select label="Office" value={f.officeId} onChange={set('officeId')} blank="None" options={(ref.data?.offices ?? []).map((o) => ({ value: o.officeId, label: o.name }))} />
            <Input label="Purchase cost" type="number" min={0} step="0.01" value={f.purchaseCost} onChange={set('purchaseCost')} />
            <button type="submit" className="primary" disabled={create.isPending}>Create asset</button>
          </form>
        </Card>
      )}
      <form className="filters" role="search" onSubmit={(e) => e.preventDefault()}>
        <Input label="Search" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <Select label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} blank="Any" options={STATUSES.map((s) => ({ value: s, label: human(s) }))} />
        <Select label="Warranty" value={warranty} onChange={(e) => { setWarranty(e.target.value); setPage(1); }} blank="Any" options={['ACTIVE', 'EXPIRING', 'EXPIRED'].map((s) => ({ value: s, label: human(s) }))} />
      </form>
      <Loading q={list} />
      <ErrorBox error={list.error} />
      {list.data?.items.length === 0 && <Empty>No assets found.</Empty>}
      {!!list.data?.items.length && (
        <Table caption="Assets">
          <thead><tr><th>Tag</th><th>Type</th><th>Model</th><th>Status</th><th>Assigned to</th><th>Warranty</th></tr></thead>
          <tbody>
            {list.data.items.map((a) => (
              <tr key={a.assetId}>
                <td><Link to={`/assets/${a.assetId}`}>{a.assetTag}</Link></td>
                <td>{a.assetType}</td><td>{[a.manufacturer, a.model].filter(Boolean).join(' ') || '-'}</td>
                <td><StatusBadge value={a.status} /></td><td>{a.assignedUserName ?? '-'}</td>
                <td>{a.warrantyState ? <Badge tone={a.warrantyState === 'EXPIRED' ? 'danger' : a.warrantyState === 'EXPIRING' ? 'warn' : 'ok'}>{human(a.warrantyState)}</Badge> : '-'} {fmtDay(a.warrantyEnd)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <Pager page={page} onPage={setPage} data={list.data} />
    </>
  );
}

export function AssetDetail() {
  const { id } = useParams();
  const user = useUser();
  const manage = hasRole(user, R.AM, R.ADMIN);
  const qc = useQueryClient();
  const toast = useToast();
  const names = useNames();
  const q = useQuery({ queryKey: ['asset', id], queryFn: () => api<Asset>(`/assets/${id}`) });
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [userId, setUserId] = useState('');
  const users = useQuery({
    queryKey: ['user-search', search], enabled: manage && search.length >= 2,
    queryFn: () => api<Page<UserView>>('/users', { query: { q: search, size: 10 } }),
  });
  const refresh = () => { void qc.invalidateQueries({ queryKey: ['asset', id] }); void qc.invalidateQueries({ queryKey: ['assets'] }); };
  const assign = useMutation({ mutationFn: () => api(`/assets/${id}/assign`, { body: { userId: Number(userId) } }), onSuccess: () => { toast.ok('Asset assigned.'); setUserId(''); refresh(); } });
  const setSt = useMutation({ mutationFn: () => api(`/assets/${id}/status`, { body: { status } }), onSuccess: () => { toast.ok('Status updated.'); setStatus(''); refresh(); } });
  const a = q.data;
  if (q.isLoading) return <Loading />;
  if (!a) return <ErrorBox error={q.error} />;
  return (
    <>
      <PageHead title={`Asset ${a.assetTag}`}><Link to="/assets" className="btn">Back to list</Link></PageHead>
      <ErrorBox error={assign.error ?? setSt.error} />
      <Card title="Details">
        <dl className="kv">
          <dt>Status</dt><dd><StatusBadge value={a.status} /></dd>
          <dt>Type</dt><dd>{a.assetType}</dd>
          <dt>Make / model</dt><dd>{[a.manufacturer, a.model].filter(Boolean).join(' ') || '-'}</dd>
          <dt>Serial number</dt><dd>{a.serialNumber ?? '-'}</dd>
          <dt>Office</dt><dd>{names.office(a.officeId)}</dd>
          <dt>Assigned to</dt><dd>{a.assignedUserName ?? '-'}</dd>
          <dt>Purchased</dt><dd>{fmtDay(a.purchaseDate)} {a.purchaseCost != null && `(${money(a.purchaseCost)})`}</dd>
          <dt>Warranty end</dt><dd>{fmtDay(a.warrantyEnd)} {a.warrantyState && <Badge>{human(a.warrantyState)}</Badge>}</dd>
        </dl>
      </Card>
      {manage && (
        <div className="grid2">
          <Card title="Assign to a user">
            <form className="form" onSubmit={(e) => { e.preventDefault(); assign.mutate(); }}>
              <Input label="Find user" value={search} onChange={(e) => setSearch(e.target.value)} hint="Type at least 2 letters of a name or email." />
              <Select label="User" required value={userId} onChange={(e) => setUserId(e.target.value)} blank="Select a user" options={(users.data?.items ?? []).map((u) => ({ value: u.userId, label: `${u.firstName} ${u.lastName} (${u.email})` }))} />
              <button type="submit" className="primary" disabled={!userId || assign.isPending}>Assign asset</button>
            </form>
          </Card>
          <Card title="Change status">
            <form className="form" onSubmit={(e) => { e.preventDefault(); setSt.mutate(); }}>
              <Select label="New status" value={status} onChange={(e) => setStatus(e.target.value)} blank="Select a status" options={STATUSES.map((s) => ({ value: s, label: human(s) }))} />
              <button type="submit" disabled={!status || setSt.isPending}>Update status</button>
            </form>
          </Card>
        </div>
      )}
      <Card title="Assignment history">
        {(a.history ?? []).length === 0 && <Empty>No assignment history.</Empty>}
        {!!a.history?.length && (
          <Table caption="Assignment history">
            <thead><tr><th>User</th><th>Assigned</th><th>Returned</th></tr></thead>
            <tbody>{a.history.map((h, i) => <tr key={i}><td>{h.userName}</td><td>{fmtDate(h.assignedAt)}</td><td>{fmtDate(h.returnedAt)}</td></tr>)}</tbody>
          </Table>
        )}
      </Card>
    </>
  );
}
