import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, download } from '../lib/api';
import { human } from '../lib/format';
import { useToast } from '../components/Toast';
import { Card, Empty, ErrorBox, Input, Loading, PageHead, Select, Table } from '../components/ui';

type Row = Record<string, unknown>;
const REPORTS = [
  { id: 'incident-volume', label: 'Incident volume', export: true },
  { id: 'sla-compliance', label: 'SLA compliance', export: true },
  { id: 'backlog-ageing', label: 'Backlog ageing', export: true },
  { id: 'workload', label: 'Workload', export: true },
  { id: 'assets', label: 'Assets', export: true },
  { id: 'requests', label: 'Requests', export: true },
  { id: 'changes', label: 'Changes', export: true },
  { id: 'problems', label: 'Problems', export: true },
];
const DIMENSIONS = ['month', 'week', 'priority', 'channel', 'team', 'service', 'office', 'status'];

function cell(v: unknown): string {
  if (v === null || v === undefined) return '-';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

function DataTable({ rows, caption }: { rows: Row[]; caption: string }) {
  if (rows.length === 0) return <Empty>No data for this range.</Empty>;
  const cols = Object.keys(rows[0]);
  return (
    <Table caption={caption}>
      <thead><tr>{cols.map((c) => <th key={c}>{human(c.replace(/([A-Z])/g, '_$1'))}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i}>{cols.map((c) => <td key={c}>{cell(r[c])}</td>)}</tr>)}</tbody>
    </Table>
  );
}

function Flat({ obj }: { obj: Row }) {
  return (
    <>
      {Object.entries(obj).map(([k, v]) => (
        Array.isArray(v) ? <div key={k}><h3>{human(k.replace(/([A-Z])/g, '_$1'))}</h3><DataTable rows={v as Row[]} caption={k} /></div>
          : v && typeof v === 'object' ? <div key={k}><h3>{human(k.replace(/([A-Z])/g, '_$1'))}</h3><Flat obj={v as Row} /></div>
            : <dl className="kv" key={k}><dt>{human(k.replace(/([A-Z])/g, '_$1'))}</dt><dd>{cell(v)}</dd></dl>
      ))}
    </>
  );
}

export function Reports() {
  const toast = useToast();
  const [name, setName] = useState('incident-volume');
  const [by, setBy] = useState('month');
  const [since, setSince] = useState('');
  const [until, setUntil] = useState('');
  const query = { by: name === 'incident-volume' ? by : undefined, since, until };
  const q = useQuery({ queryKey: ['report', name, by, since, until], queryFn: () => api<Row[] | Row>(`/reports/${name}`, { query }) });
  const summary = useQuery({ queryKey: ['report-summary', since, until], queryFn: () => api<Row>('/reports/summary', { query: { since, until } }) });
  return (
    <>
      <PageHead title="Reports">
        <button type="button" onClick={() => download(`/reports/${name}/export`, query, `${name}.csv`).catch((e: Error) => toast.error(e.message))}>Export CSV</button>
      </PageHead>
      <form className="filters" onSubmit={(e) => e.preventDefault()}>
        <Select label="Report" value={name} onChange={(e) => setName(e.target.value)} options={REPORTS.map((r) => ({ value: r.id, label: r.label }))} />
        {name === 'incident-volume' && <Select label="Group by" value={by} onChange={(e) => setBy(e.target.value)} options={DIMENSIONS.map((d) => ({ value: d, label: human(d) }))} />}
        <Input label="Since" type="date" value={since} onChange={(e) => setSince(e.target.value)} />
        <Input label="Until" type="date" value={until} onChange={(e) => setUntil(e.target.value)} />
      </form>
      <Card title="Summary">
        <Loading q={summary} />
        <ErrorBox error={summary.error} />
        {summary.data && <div className="kvgrid">{Object.entries(summary.data).map(([k, v]) => <div key={k}><span className="muted">{human(k.replace(/([A-Z])/g, '_$1'))}</span><strong>{cell(v)}</strong></div>)}</div>}
      </Card>
      <Card title={REPORTS.find((r) => r.id === name)?.label}>
        <Loading q={q} />
        <ErrorBox error={q.error} />
        {q.data && (Array.isArray(q.data) ? <DataTable rows={q.data} caption={name} /> : <Flat obj={q.data} />)}
      </Card>
    </>
  );
}
