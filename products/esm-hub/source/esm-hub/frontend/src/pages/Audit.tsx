import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, download } from '../lib/api';
import { fmtDate } from '../lib/format';
import type { AuditEntry, Page } from '../lib/types';
import { useToast } from '../components/Toast';
import { Empty, ErrorBox, Input, Loading, PageHead, Pager, Select, Table } from '../components/ui';

const SERVICES = ['directory', 'incident', 'request', 'change', 'asset', 'knowledge', 'notification', 'reporting'];

export function Audit() {
  const toast = useToast();
  const [f, setF] = useState({ service: '', entityType: '', entityId: '', action: '', actorId: '', from: '', to: '' });
  const [applied, setApplied] = useState(f);
  const [page, setPage] = useState(1);
  const toIso = (s: string, end = false) => (s ? new Date(`${s}T${end ? '23:59:59' : '00:00:00'}`).toISOString() : '');
  const query = { ...applied, from: toIso(applied.from), to: toIso(applied.to, true) };
  const list = useQuery({ queryKey: ['audit', applied, page], queryFn: () => api<Page<AuditEntry>>('/audit', { query: { ...query, page, size: 25 } }) });
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  return (
    <>
      <PageHead title="Audit log">
        <button type="button" onClick={() => download('/audit/export', query, 'audit.csv').catch((e: Error) => toast.error(e.message))}>Export CSV</button>
      </PageHead>
      <form className="filters" role="search" onSubmit={(e) => { e.preventDefault(); setApplied(f); setPage(1); }}>
        <Select label="Service" value={f.service} onChange={set('service')} blank="Any" options={SERVICES.map((s) => ({ value: s, label: s }))} />
        <Input label="Entity type" value={f.entityType} onChange={set('entityType')} />
        <Input label="Entity ID" value={f.entityId} onChange={set('entityId')} />
        <Input label="Action" value={f.action} onChange={set('action')} />
        <Input label="Actor user ID" type="number" min={1} value={f.actorId} onChange={set('actorId')} />
        <Input label="From" type="date" value={f.from} onChange={set('from')} />
        <Input label="To" type="date" value={f.to} onChange={set('to')} />
        <button type="submit" className="primary">Apply filters</button>
      </form>
      <Loading q={list} />
      <ErrorBox error={list.error} />
      {list.data?.items.length === 0 && <Empty>No audit entries match.</Empty>}
      {!!list.data?.items.length && (
        <Table caption="Audit entries">
          <thead><tr><th>When</th><th>Service</th><th>Actor</th><th>Entity</th><th>Action</th><th>Changes</th></tr></thead>
          <tbody>
            {list.data.items.map((a) => (
              <tr key={a.auditId}>
                <td>{fmtDate(a.occurredAt)}</td><td>{a.service}</td><td>{a.actorUserId ?? '-'}</td><td>{a.entityType} {a.entityId}</td><td>{a.action}</td>
                <td>{(a.oldValues != null || a.newValues != null) ? (
                  <details><summary>View</summary><pre>{JSON.stringify({ old: a.oldValues, new: a.newValues }, null, 2)}</pre></details>
                ) : '-'}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <Pager page={page} onPage={setPage} data={list.data} />
    </>
  );
}
