import { useState } from 'react';
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, asList } from '../lib/api';
import { useUser } from '../lib/auth';
import { hasRole, R } from '../lib/roles';
import { fmtDay, human } from '../lib/format';
import { useNames, usePriorities, useReference } from '../lib/hooks';
import type { Calendar, Page, Rule, SlaPolicy, UserView } from '../lib/types';
import { useToast } from '../components/Toast';
import { Badge, Card, Empty, ErrorBox, Input, Loading, PageHead, Pager, Select, Table } from '../components/ui';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

function Users() {
  const qc = useQueryClient();
  const toast = useToast();
  const ref = useReference();
  const [q, setQ] = useState('');
  const [inactive, setInactive] = useState(false);
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<UserView | null>(null);
  const [show, setShow] = useState(false);
  const list = useQuery({ queryKey: ['admin-users', q, inactive, page], queryFn: () => api<Page<UserView>>('/users', { query: { q, includeInactive: inactive, page, size: 25 } }) });
  const roles = ref.data?.roles ?? [];
  const refresh = () => void qc.invalidateQueries({ queryKey: ['admin-users'] });

  const [n, setN] = useState({ employeeNo: '', firstName: '', lastName: '', email: '', initialPassword: '', roles: ['EMPLOYEE'] as string[] });
  const create = useMutation({
    mutationFn: () => api('/admin/users', { body: { ...n, initialPassword: n.initialPassword || undefined } }),
    onSuccess: () => { toast.ok('User created.'); setShow(false); refresh(); },
  });
  const [eRoles, setERoles] = useState<string[]>([]);
  const [eStatus, setEStatus] = useState('ACTIVE');
  const [eTeams, setETeams] = useState<number[]>([]);
  const [pw, setPw] = useState('');
  const save = useMutation({
    mutationFn: () => api(`/admin/users/${editing!.userId}`, { method: 'PATCH', body: { roles: eRoles, employmentStatus: eStatus, teamIds: eTeams } }),
    onSuccess: () => { toast.ok('User updated.'); setEditing(null); refresh(); },
  });
  const setPassword = useMutation({
    mutationFn: () => api(`/admin/users/${editing!.userId}/password`, { body: { newPassword: pw } }),
    onSuccess: () => { toast.ok('Password reset.'); setPw(''); },
  });
  const toggle = <T,>(arr: T[], v: T) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  return (
    <>
      <div className="actions"><button type="button" className="primary" onClick={() => setShow(!show)} aria-expanded={show}>New user</button></div>
      {show && (
        <Card title="New user">
          <form className="form" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
            <ErrorBox error={create.error} />
            <Input label="Employee number" required value={n.employeeNo} onChange={(e) => setN({ ...n, employeeNo: e.target.value })} />
            <Input label="First name" required value={n.firstName} onChange={(e) => setN({ ...n, firstName: e.target.value })} />
            <Input label="Last name" required value={n.lastName} onChange={(e) => setN({ ...n, lastName: e.target.value })} />
            <Input label="Email" type="email" required value={n.email} onChange={(e) => setN({ ...n, email: e.target.value })} />
            <Input label="Initial password" type="password" autoComplete="new-password" value={n.initialPassword} onChange={(e) => setN({ ...n, initialPassword: e.target.value })} />
            <fieldset><legend>Roles</legend>
              {roles.map((r) => <label className="inline" key={r}><input type="checkbox" checked={n.roles.includes(r)} onChange={() => setN({ ...n, roles: toggle(n.roles, r) })} /> {human(r)}</label>)}
            </fieldset>
            <button type="submit" className="primary" disabled={create.isPending || n.roles.length === 0}>Create user</button>
          </form>
        </Card>
      )}
      {editing && (
        <Card title={`Edit ${editing.firstName} ${editing.lastName}`}>
          <ErrorBox error={save.error ?? setPassword.error} />
          <form className="form" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
            <Select label="Employment status" value={eStatus} onChange={(e) => setEStatus(e.target.value)} options={['ACTIVE', 'INACTIVE', 'ON_LEAVE'].map((s) => ({ value: s, label: human(s) }))} />
            <fieldset><legend>Roles</legend>
              {roles.map((r) => <label className="inline" key={r}><input type="checkbox" checked={eRoles.includes(r)} onChange={() => setERoles(toggle(eRoles, r))} /> {human(r)}</label>)}
            </fieldset>
            <fieldset><legend>Teams</legend>
              {(ref.data?.teams ?? []).map((t) => <label className="inline" key={t.teamId}><input type="checkbox" checked={eTeams.includes(t.teamId)} onChange={() => setETeams(toggle(eTeams, t.teamId))} /> {t.name}</label>)}
            </fieldset>
            <div className="actions">
              <button type="submit" className="primary" disabled={save.isPending}>Save user</button>
              <button type="button" onClick={() => setEditing(null)}>Cancel</button>
            </div>
          </form>
          <form className="filters" onSubmit={(e) => { e.preventDefault(); setPassword.mutate(); }}>
            <Input label="Set new password" type="password" autoComplete="new-password" required value={pw} onChange={(e) => setPw(e.target.value)} />
            <button type="submit" disabled={setPassword.isPending}>Reset password</button>
          </form>
        </Card>
      )}
      <form className="filters" role="search" onSubmit={(e) => e.preventDefault()}>
        <Input label="Search users" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        <label className="inline"><input type="checkbox" checked={inactive} onChange={(e) => setInactive(e.target.checked)} /> Include inactive</label>
      </form>
      <Loading q={list} />
      <ErrorBox error={list.error} />
      {!!list.data?.items.length && (
        <Table caption="Users">
          <thead><tr><th>Name</th><th>Email</th><th>Status</th><th>Roles</th><th><span className="sr-only">Actions</span></th></tr></thead>
          <tbody>
            {list.data.items.map((u) => (
              <tr key={u.userId}>
                <td>{u.firstName} {u.lastName}</td><td>{u.email}</td><td>{human(u.employmentStatus)}</td><td>{u.roles.map(human).join(', ')}</td>
                <td><button type="button" onClick={() => { setEditing(u); setERoles(u.roles); setEStatus(u.employmentStatus); setETeams(u.teamIds); }} aria-label={`Edit ${u.email}`}>Edit</button></td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <Pager page={page} onPage={setPage} data={list.data} />
    </>
  );
}

function Sla() {
  const qc = useQueryClient();
  const toast = useToast();
  const prios = usePriorities();
  const ref = useReference();
  const list = useQuery({ queryKey: ['sla'], queryFn: async () => asList(await api<SlaPolicy[] | { items: SlaPolicy[] }>('/admin/sla-policies')) });
  const [f, setF] = useState({ name: '', priorityId: '3', serviceId: '', businessHoursOnly: true, responseTargetMinutes: '60', resolutionTargetMinutes: '480', effectiveFrom: new Date().toISOString().slice(0, 10) });
  const create = useMutation({
    mutationFn: () => api('/admin/sla-policies', {
      body: { ...f, priorityId: Number(f.priorityId), serviceId: f.serviceId ? Number(f.serviceId) : undefined, responseTargetMinutes: Number(f.responseTargetMinutes), resolutionTargetMinutes: Number(f.resolutionTargetMinutes) },
    }),
    onSuccess: () => { toast.ok('SLA policy created.'); setF({ ...f, name: '' }); void qc.invalidateQueries({ queryKey: ['sla'] }); },
  });
  const names = useNames();
  return (
    <>
      <Card title="New SLA policy">
        <form className="form" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
          <ErrorBox error={create.error} />
          <Input label="Name" required minLength={2} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
          <Select label="Priority" value={f.priorityId} onChange={(e) => setF({ ...f, priorityId: e.target.value })} options={(prios.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />
          <Select label="Service" value={f.serviceId} onChange={(e) => setF({ ...f, serviceId: e.target.value })} blank="All services" options={(ref.data?.services ?? []).map((s) => ({ value: s.serviceId, label: s.name }))} />
          <Input label="Response target (minutes)" type="number" min={1} required value={f.responseTargetMinutes} onChange={(e) => setF({ ...f, responseTargetMinutes: e.target.value })} />
          <Input label="Resolution target (minutes)" type="number" min={1} required value={f.resolutionTargetMinutes} onChange={(e) => setF({ ...f, resolutionTargetMinutes: e.target.value })} />
          <Input label="Effective from" type="date" required value={f.effectiveFrom} onChange={(e) => setF({ ...f, effectiveFrom: e.target.value })} />
          <label className="inline"><input type="checkbox" checked={f.businessHoursOnly} onChange={(e) => setF({ ...f, businessHoursOnly: e.target.checked })} /> Business hours only</label>
          <button type="submit" className="primary" disabled={create.isPending}>Create policy</button>
        </form>
      </Card>
      <Loading q={list} />
      <ErrorBox error={list.error} />
      {list.data?.length === 0 && <Empty>No SLA policies.</Empty>}
      {!!list.data?.length && (
        <Table caption="SLA policies">
          <thead><tr><th>Name</th><th>Priority</th><th>Service</th><th>Response</th><th>Resolution</th><th>Hours</th><th>From</th><th>To</th><th>Ver.</th></tr></thead>
          <tbody>
            {list.data.map((p) => (
              <tr key={p.id}><td>{p.name}</td><td>{prios.data?.find((x) => x.id === p.priorityId)?.name ?? p.priorityId}</td><td>{p.serviceId ? names.service(p.serviceId) : 'All'}</td>
                <td>{p.responseTargetMinutes} min</td><td>{p.resolutionTargetMinutes} min</td><td>{p.businessHoursOnly ? 'Business' : '24x7'}</td><td>{fmtDay(p.effectiveFrom)}</td><td>{fmtDay(p.effectiveTo)}</td><td>{p.version}</td></tr>
            ))}
          </tbody>
        </Table>
      )}
    </>
  );
}

function Calendars() {
  const qc = useQueryClient();
  const toast = useToast();
  const list = useQuery({ queryKey: ['calendars'], queryFn: async () => asList(await api<Calendar[] | { items: Calendar[] }>('/admin/calendars')) });
  const [name, setName] = useState('');
  const [tz, setTz] = useState('UTC');
  const [start, setStart] = useState('09:00');
  const [end, setEnd] = useState('17:00');
  const [days, setDays] = useState<number[]>([0, 1, 2, 3, 4]);
  const [holiday, setHoliday] = useState('');
  const [holidayName, setHolidayName] = useState('');
  const create = useMutation({
    mutationFn: () => api('/admin/calendars', {
      body: {
        name, timezone: tz, hours: days.map((d) => ({ weekday: d, startTime: start, endTime: end })),
        holidays: holiday ? [{ holidayDate: holiday, name: holidayName || 'Holiday' }] : [],
      },
    }),
    onSuccess: () => { toast.ok('Calendar created.'); setName(''); void qc.invalidateQueries({ queryKey: ['calendars'] }); },
  });
  return (
    <>
      <Card title="New business calendar">
        <form className="form" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
          <ErrorBox error={create.error} />
          <Input label="Name" required minLength={2} value={name} onChange={(e) => setName(e.target.value)} />
          <Input label="Time zone" required value={tz} onChange={(e) => setTz(e.target.value)} hint="IANA name, e.g. Europe/London" />
          <Input label="Opens" type="time" required value={start} onChange={(e) => setStart(e.target.value)} />
          <Input label="Closes" type="time" required value={end} onChange={(e) => setEnd(e.target.value)} />
          <fieldset><legend>Working days</legend>
            {DAYS.map((d, i) => <label className="inline" key={d}><input type="checkbox" checked={days.includes(i)} onChange={() => setDays(days.includes(i) ? days.filter((x) => x !== i) : [...days, i].sort())} /> {d}</label>)}
          </fieldset>
          <Input label="Holiday date (optional)" type="date" value={holiday} onChange={(e) => setHoliday(e.target.value)} />
          <Input label="Holiday name" value={holidayName} onChange={(e) => setHolidayName(e.target.value)} />
          <button type="submit" className="primary" disabled={create.isPending || days.length === 0}>Create calendar</button>
        </form>
      </Card>
      <Loading q={list} />
      <ErrorBox error={list.error} />
      {list.data?.length === 0 && <Empty>No calendars.</Empty>}
      <div className="cards">
        {list.data?.map((c) => (
          <article key={c.id} className="card">
            <h2>{c.name}</h2>
            <p className="muted">{c.timezone}</p>
            <ul>{c.hours.map((h, i) => <li key={i}>{DAYS[h.weekday]}: {h.startTime.slice(0, 5)} - {h.endTime.slice(0, 5)}</li>)}</ul>
            {!!c.holidays?.length && <p>Holidays: {c.holidays.map((h) => `${h.name} (${h.holidayDate})`).join(', ')}</p>}
          </article>
        ))}
      </div>
    </>
  );
}

function Rules() {
  const qc = useQueryClient();
  const toast = useToast();
  const ref = useReference();
  const prios = usePriorities();
  const names = useNames();
  const list = useQuery({ queryKey: ['rules'], queryFn: async () => asList(await api<Rule[] | { items: Rule[] }>('/admin/assignment-rules')) });
  const [f, setF] = useState({ serviceId: '', priorityId: '', teamId: '', sortOrder: '100' });
  const refresh = () => void qc.invalidateQueries({ queryKey: ['rules'] });
  const create = useMutation({
    mutationFn: () => api('/admin/assignment-rules', {
      body: { serviceId: f.serviceId ? Number(f.serviceId) : undefined, priorityId: f.priorityId ? Number(f.priorityId) : undefined, teamId: Number(f.teamId), sortOrder: Number(f.sortOrder), active: true },
    }),
    onSuccess: () => { toast.ok('Rule created.'); refresh(); },
  });
  const toggle = useMutation({
    mutationFn: (r: Rule) => api(`/admin/assignment-rules/${r.id}`, { method: 'PUT', body: { serviceId: r.serviceId, priorityId: r.priorityId, teamId: r.teamId, sortOrder: r.sortOrder, active: !r.active } }),
    onSuccess: refresh,
  });
  return (
    <>
      <Card title="New assignment rule">
        <form className="form" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
          <ErrorBox error={create.error ?? toggle.error} />
          <Select label="Service" value={f.serviceId} onChange={(e) => setF({ ...f, serviceId: e.target.value })} blank="Any service" options={(ref.data?.services ?? []).map((s) => ({ value: s.serviceId, label: s.name }))} />
          <Select label="Priority" value={f.priorityId} onChange={(e) => setF({ ...f, priorityId: e.target.value })} blank="Any priority" options={(prios.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />
          <Select label="Team" required value={f.teamId} onChange={(e) => setF({ ...f, teamId: e.target.value })} blank="Select a team" options={(ref.data?.teams ?? []).map((t) => ({ value: t.teamId, label: t.name }))} />
          <Input label="Sort order" type="number" min={0} max={10000} value={f.sortOrder} onChange={(e) => setF({ ...f, sortOrder: e.target.value })} />
          <button type="submit" className="primary" disabled={!f.teamId || create.isPending}>Create rule</button>
        </form>
      </Card>
      <Loading q={list} />
      {list.data?.length === 0 && <Empty>No rules.</Empty>}
      {!!list.data?.length && (
        <Table caption="Assignment rules">
          <thead><tr><th>Order</th><th>Service</th><th>Priority</th><th>Team</th><th>Active</th></tr></thead>
          <tbody>
            {[...list.data].sort((a, b) => a.sortOrder - b.sortOrder).map((r) => (
              <tr key={r.id}>
                <td>{r.sortOrder}</td><td>{r.serviceId ? names.service(r.serviceId) : 'Any'}</td>
                <td>{r.priorityId ? prios.data?.find((p) => p.id === r.priorityId)?.name ?? r.priorityId : 'Any'}</td><td>{names.team(r.teamId)}</td>
                <td><button type="button" onClick={() => toggle.mutate(r)} aria-pressed={r.active}>{r.active ? <Badge tone="ok">Active</Badge> : <Badge tone="muted">Inactive</Badge>}</button></td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </>
  );
}

export function Admin() {
  const user = useUser();
  const isAdmin = hasRole(user, R.ADMIN);
  return (
    <>
      <PageHead title="Administration" />
      <nav className="tabs" aria-label="Administration sections">
        {isAdmin && <NavLink to="/admin/users">Users</NavLink>}
        <NavLink to="/admin/sla">SLA policies</NavLink>
        <NavLink to="/admin/calendars">Calendars</NavLink>
        <NavLink to="/admin/rules">Assignment rules</NavLink>
      </nav>
      <Routes>
        <Route index element={<Navigate to={isAdmin ? 'users' : 'sla'} replace />} />
        {isAdmin && <Route path="users" element={<Users />} />}
        <Route path="sla" element={<Sla />} />
        <Route path="calendars" element={<Calendars />} />
        <Route path="rules" element={<Rules />} />
        <Route path="*" element={<Navigate to="sla" replace />} />
      </Routes>
    </>
  );
}
