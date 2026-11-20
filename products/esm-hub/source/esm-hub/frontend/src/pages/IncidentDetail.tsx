import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useUser } from '../lib/auth';
import { hasRole, R } from '../lib/roles';
import { fmtDate, human } from '../lib/format';
import { useNames, useReference, useTeamMembers } from '../lib/hooks';
import type { Incident } from '../lib/types';
import { useToast } from '../components/Toast';
import { Badge, Card, Empty, ErrorBox, Input, Loading, PageHead, Select, StatusBadge, Textarea } from '../components/ui';
import { SlaBadge } from './Incidents';

const RESOLUTION_CODES = ['SOLVED', 'WORKAROUND', 'NO_FAULT_FOUND', 'DUPLICATE', 'USER_ERROR', 'THIRD_PARTY'];

export function IncidentDetail() {
  const { id } = useParams();
  const user = useUser();
  const qc = useQueryClient();
  const toast = useToast();
  const names = useNames();
  const key = ['incident', id];
  const q = useQuery({ queryKey: key, queryFn: () => api<Incident>(`/incidents/${id}`) });
  const i = q.data;
  const staff = hasRole(user, R.DESK, R.TECH, R.LEAD, R.SM, R.CM, R.AUDITOR, R.ADMIN);
  const desk = hasRole(user, R.DESK, R.LEAD);
  const isRequester = i ? String(i.requesterId) === user.sub : false;

  function useAction<V>(fn: (v: V) => Promise<unknown>, msg: string, after?: () => void) {
    return useMutation({
      mutationFn: fn,
      onSuccess: () => { toast.ok(msg); after?.(); void qc.invalidateQueries({ queryKey: key }); void qc.invalidateQueries({ queryKey: ['incidents'] }); },
    });
  }

  // Assign
  const ref = useReference();
  const [teamId, setTeamId] = useState('');
  const [userId, setUserId] = useState('');
  const members = useTeamMembers(teamId);
  const canAssign = desk || (hasRole(user, R.TECH) && !!i);
  const assign = useAction(() => api(`/incidents/${id}/assign`, { body: { teamId: teamId ? Number(teamId) : undefined, userId: userId ? Number(userId) : undefined } }), 'Assignment saved.');

  // Status
  const [status, setStatus] = useState('');
  const [code, setCode] = useState('SOLVED');
  const [notes, setNotes] = useState('');
  const changeStatus = useAction(() => api(`/incidents/${id}/status`, { body: { status, resolutionCode: status === 'RESOLVED' ? code : undefined, resolutionNotes: status === 'RESOLVED' ? notes : undefined } }), 'Status updated.', () => setStatus(''));

  // Reopen
  const [reason, setReason] = useState('');
  const reopen = useAction(() => api(`/incidents/${id}/reopen`, { body: { reason } }), 'Incident reopened.', () => setReason(''));

  // Comments
  const [body, setBody] = useState('');
  const [internal, setInternal] = useState(false);
  const comment = useAction(() => api(`/incidents/${id}/comments`, { body: { body, internal: staff && internal } }), 'Comment added.', () => { setBody(''); setInternal(false); });

  // Worklog
  const [minutes, setMinutes] = useState('15');
  const [work, setWork] = useState('');
  const worklog = useAction(() => api(`/incidents/${id}/worklogs`, { body: { minutesSpent: Number(minutes), workDescription: work } }), 'Work logged.', () => setWork(''));

  const rate = useAction((score: number) => api(`/incidents/${id}/satisfaction`, { body: { score } }), 'Thanks for your feedback.');

  if (q.isLoading) return <Loading />;
  if (!i) return <ErrorBox error={q.error} />;
  const transitions = i.allowedTransitions ?? [];

  return (
    <>
      <PageHead title={`${i.ticketNo}: ${i.title}`}>
        <Link to="/incidents" className="btn">Back to list</Link>
      </PageHead>
      <ErrorBox error={assign.error ?? changeStatus.error ?? reopen.error ?? comment.error ?? worklog.error ?? rate.error} />
      <div className="grid2">
        <Card title="Details">
          <dl className="kv">
            <dt>Status</dt><dd data-testid="incident-status"><StatusBadge value={i.status} /></dd>
            <dt>Priority</dt><dd>{i.priority}</dd>
            <dt>Requester</dt><dd>{i.requesterName ?? i.requesterId}</dd>
            <dt>Team</dt><dd>{i.teamName ?? names.team(i.assignedTeamId)}</dd>
            <dt>Assignee</dt><dd>{i.assigneeName ?? 'Unassigned'}</dd>
            <dt>Service</dt><dd>{names.service(i.serviceId)}</dd>
            <dt>Channel</dt><dd>{human(i.channel)}</dd>
            <dt>Created</dt><dd>{fmtDate(i.createdAt)}</dd>
            <dt>Resolved</dt><dd>{fmtDate(i.resolvedAt)}</dd>
            {i.reopenedCount > 0 && (<><dt>Reopened</dt><dd>{i.reopenedCount} time(s)</dd></>)}
          </dl>
          <h3>Description</h3>
          <p className="pre">{i.description}</p>
          {i.resolutionCode && (<><h3>Resolution</h3><p><Badge>{human(i.resolutionCode)}</Badge></p><p className="pre">{i.resolutionNotes}</p></>)}
        </Card>
        <Card title="SLA">
          <dl className="kv">
            <dt>Resolution</dt><dd><SlaBadge i={i} /> due {fmtDate(i.dueAt)}</dd>
            <dt>First response</dt>
            <dd>
              {i.firstResponseAt ? <Badge tone={i.responseBreached ? 'danger' : 'ok'}>{i.responseBreached ? 'Breached' : 'Met'}</Badge> : <Badge tone={i.responseBreached ? 'danger' : 'info'}>{i.responseBreached ? 'Breached' : 'Awaiting'}</Badge>}
              {' '}due {fmtDate(i.responseDueAt)}
            </dd>
            {i.slaPaused && (<><dt>Clock</dt><dd><Badge tone="muted">Paused</Badge></dd></>)}
          </dl>
          {i.problems && i.problems.length > 0 && (
            <>
              <h3>Linked problems</h3>
              <ul>{i.problems.map((p) => <li key={p.id}><Link to={`/problems/${p.id}`}>{p.problemNo}</Link> {p.title}{p.workaround ? ` - Workaround: ${p.workaround}` : ''}</li>)}</ul>
            </>
          )}
          {(i.status === 'RESOLVED' || i.status === 'CLOSED') && isRequester && i.satisfactionScore == null && (
            <fieldset className="rating">
              <legend>Rate this resolution</legend>
              {[1, 2, 3, 4, 5].map((s) => <button key={s} type="button" onClick={() => rate.mutate(s)} aria-label={`${s} out of 5`}>{s}</button>)}
            </fieldset>
          )}
          {i.satisfactionScore != null && <p>Satisfaction: {i.satisfactionScore} / 5</p>}
        </Card>
      </div>

      <div className="grid2">
        {canAssign && (
          <Card title="Assign">
            <form className="form" onSubmit={(e) => { e.preventDefault(); assign.mutate(undefined); }}>
              <Select label="Team" value={teamId} onChange={(e) => { setTeamId(e.target.value); setUserId(''); }} blank="Select a team" options={(ref.data?.teams ?? []).filter((t) => t.active).map((t) => ({ value: t.teamId, label: t.name }))} />
              <Select label="Member" value={userId} onChange={(e) => setUserId(e.target.value)} blank={teamId ? 'Any member' : 'Pick a team first'} disabled={!teamId} options={(members.data ?? []).map((m) => ({ value: m.userId, label: m.name }))} />
              <button type="submit" className="primary" disabled={(!teamId && !userId) || assign.isPending}>Assign</button>
            </form>
          </Card>
        )}
        {transitions.length > 0 && (
          <Card title="Change status">
            <form className="form" onSubmit={(e) => { e.preventDefault(); changeStatus.mutate(undefined); }}>
              <Select label="New status" value={status} onChange={(e) => setStatus(e.target.value)} blank="Select a status" options={transitions.map((t) => ({ value: t, label: human(t) }))} />
              {status === 'RESOLVED' && (
                <>
                  <Select label="Resolution code" value={code} onChange={(e) => setCode(e.target.value)} options={RESOLUTION_CODES.map((c) => ({ value: c, label: human(c) }))} />
                  <Textarea label="Resolution notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
                </>
              )}
              <button type="submit" className="primary" disabled={!status || changeStatus.isPending}>Update status</button>
            </form>
          </Card>
        )}
        {i.status === 'RESOLVED' && (isRequester || desk) && (
          <Card title="Reopen">
            <form className="form" onSubmit={(e) => { e.preventDefault(); reopen.mutate(undefined); }}>
              <Textarea label="Reason for reopening" required minLength={3} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
              <button type="submit" disabled={reopen.isPending}>Reopen incident</button>
            </form>
          </Card>
        )}
      </div>

      <Card title="Comments">
        {(i.comments ?? []).length === 0 && <Empty>No comments yet.</Empty>}
        <ul className="list">
          {(i.comments ?? []).map((c) => (
            <li key={c.id} className={c.internal ? 'internal' : ''}>
              <div>
                <strong>{c.authorName}</strong> {c.internal && <Badge tone="warn">Internal note</Badge>}
                <p className="pre">{c.body}</p>
                <small className="muted">{fmtDate(c.createdAt)}</small>
              </div>
            </li>
          ))}
        </ul>
        <form className="form" onSubmit={(e) => { e.preventDefault(); comment.mutate(undefined); }}>
          <Textarea label="Add a comment" required rows={3} value={body} onChange={(e) => setBody(e.target.value)} />
          {staff && <label className="inline"><input type="checkbox" checked={internal} onChange={(e) => setInternal(e.target.checked)} /> Internal note (hidden from the requester)</label>}
          <button type="submit" disabled={comment.isPending}>Post comment</button>
        </form>
      </Card>

      {i.worklogs && (
        <Card title="Work log">
          {i.worklogs.length === 0 && <Empty>No work logged.</Empty>}
          <ul className="list">
            {i.worklogs.map((w) => <li key={w.id}><div><strong>{w.userName}</strong> - {w.minutesSpent} min<p className="pre">{w.workDescription}</p><small className="muted">{fmtDate(w.loggedAt)}</small></div></li>)}
          </ul>
          {i.canWork && (
            <form className="form" onSubmit={(e) => { e.preventDefault(); worklog.mutate(undefined); }}>
              <Input label="Minutes spent" type="number" min={1} max={1440} required value={minutes} onChange={(e) => setMinutes(e.target.value)} />
              <Textarea label="Work description" required minLength={3} rows={2} value={work} onChange={(e) => setWork(e.target.value)} />
              <button type="submit" disabled={worklog.isPending}>Log work</button>
            </form>
          )}
        </Card>
      )}

      <Card title="Timeline">
        {(i.events ?? []).length === 0 && <Empty>No events.</Empty>}
        <ol className="timeline">
          {(i.events ?? []).map((e, n) => (
            <li key={n}>
              <strong>{human(e.eventType)}</strong>{e.fromValue || e.toValue ? `: ${e.fromValue ?? ''} -> ${e.toValue ?? ''}` : ''}
              <br /><small className="muted">{fmtDate(e.occurredAt)}</small>
            </li>
          ))}
        </ol>
      </Card>
    </>
  );
}
