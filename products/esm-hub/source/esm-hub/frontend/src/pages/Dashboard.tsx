import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api, asList } from '../lib/api';
import { useUser } from '../lib/auth';
import { hasRole, REPORT_ROLES } from '../lib/roles';
import { fmtDate } from '../lib/format';
import type { ApprovalRow, Incident, Page } from '../lib/types';
import { BarChart, Card, Empty, ErrorBox, Loading, PageHead, StatusBadge } from '../components/ui';

type Row = Record<string, string | number | null>;

const KPIS: [string, string, string][] = [
  ['created', 'Incidents created', ''], ['resolved', 'Resolved', ''], ['openBacklog', 'Open backlog', ''],
  ['unassigned', 'Unassigned', ''], ['openBreached', 'Open breached', ''], ['resolutionSlaPct', 'Resolution SLA', '%'],
  ['responseSlaPct', 'Response SLA', '%'], ['avgCsat', 'Avg CSAT', ''], ['openRequests', 'Open requests', ''],
];

function ReportingDashboard() {
  const summary = useQuery({ queryKey: ['rpt', 'summary'], queryFn: () => api<Record<string, number | string | null>>('/reports/summary') });
  const month = useQuery({ queryKey: ['rpt', 'vol', 'month'], queryFn: () => api<Row[]>('/reports/incident-volume', { query: { by: 'month' } }) });
  const prio = useQuery({ queryKey: ['rpt', 'vol', 'priority'], queryFn: () => api<Row[]>('/reports/incident-volume', { query: { by: 'priority' } }) });
  const age = useQuery({ queryKey: ['rpt', 'age'], queryFn: () => api<Row[]>('/reports/backlog-ageing') });
  const ageByBucket = new Map<string, number>();
  (age.data ?? []).forEach((r) => ageByBucket.set(String(r.bucket), (ageByBucket.get(String(r.bucket)) ?? 0) + Number(r.count)));
  const toRows = (d?: Row[]) => (d ?? []).map((r) => ({ label: String(r.key), value: Number(r.count), extra: Number(r.breached) }));

  return (
    <>
      <Loading q={summary} />
      <ErrorBox error={summary.error ?? month.error} />
      <div className="kpis" role="list">
        {KPIS.map(([k, label, unit]) => (
          <div className="kpi" role="listitem" key={k}>
            <div className="kpi-value">{summary.data?.[k] ?? '-'}{summary.data?.[k] != null ? unit : ''}</div>
            <div className="kpi-label">{label}</div>
          </div>
        ))}
      </div>
      <div className="grid2">
        <Card><BarChart title="Incidents by month" rows={toRows(month.data)} /></Card>
        <Card><BarChart title="Incidents by priority" rows={toRows(prio.data)} /></Card>
        <Card><BarChart title="Open backlog by age" rows={[...ageByBucket].map(([label, value]) => ({ label, value }))} /></Card>
      </div>
    </>
  );
}

function MyWork() {
  const inc = useQuery({ queryKey: ['dash', 'incidents'], queryFn: () => api<Page<Incident>>('/incidents', { query: { view: 'mine', size: 5 } }) });
  const apr = useQuery({
    queryKey: ['approvals'],
    queryFn: async () => {
      const [r, c] = await Promise.all([api<ApprovalRow[] | Page<ApprovalRow>>('/approvals'), api<ApprovalRow[] | Page<ApprovalRow>>('/change-approvals')]);
      return [...asList(r).map((a) => ({ ...a, kind: 'request' })), ...asList(c).map((a) => ({ ...a, kind: 'change' }))];
    },
  });
  const pending = (apr.data ?? []).filter((a) => !a.decidedAt);
  return (
    <div className="grid2">
      <Card title="My tickets">
        <Loading q={inc} />
        <ErrorBox error={inc.error} />
        {inc.data?.items.length === 0 && <Empty>You have no tickets.</Empty>}
        <ul className="list">
          {inc.data?.items.map((i) => (
            <li key={i.id}>
              <div><Link to={`/incidents/${i.id}`}>{i.ticketNo}</Link> {i.title}<br /><small className="muted">{fmtDate(i.createdAt)}</small></div>
              <StatusBadge value={i.status} />
            </li>
          ))}
        </ul>
        <p><Link to="/incidents">All my incidents</Link> | <Link to="/incidents/new">Report an issue</Link></p>
      </Card>
      <Card title="My approvals">
        <Loading q={apr} />
        {pending.length === 0 && !apr.isLoading && <Empty>No approvals waiting for you.</Empty>}
        <ul className="list">
          {pending.slice(0, 5).map((a) => (
            <li key={`${a.requestId ?? a.changeId}-${a.approvalId}`}><div>{a.reference} - {a.title}</div></li>
          ))}
        </ul>
        <p><Link to="/approvals">Open approvals inbox</Link></p>
      </Card>
    </div>
  );
}

export function Dashboard() {
  const user = useUser();
  const reporting = hasRole(user, ...REPORT_ROLES);
  return (
    <>
      <PageHead title={`Welcome, ${user.name.split(' ')[0] || 'there'}`} />
      {reporting && <ReportingDashboard />}
      <MyWork />
    </>
  );
}
