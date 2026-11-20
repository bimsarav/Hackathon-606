import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, asList } from '../lib/api';
import { fmtDate } from '../lib/format';
import type { ApprovalRow, Page } from '../lib/types';
import { useToast } from '../components/Toast';
import { Card, Empty, ErrorBox, Loading, PageHead, StatusBadge, Textarea } from '../components/ui';

type Row = ApprovalRow & { kind: 'request' | 'change' };

export function Approvals() {
  const qc = useQueryClient();
  const toast = useToast();
  const q = useQuery({
    queryKey: ['approvals'],
    queryFn: async (): Promise<Row[]> => {
      const [r, c] = await Promise.all([
        api<ApprovalRow[] | Page<ApprovalRow>>('/approvals'),
        api<ApprovalRow[] | Page<ApprovalRow>>('/change-approvals'),
      ]);
      return [...asList(r).map((a) => ({ ...a, kind: 'request' as const })), ...asList(c).map((a) => ({ ...a, kind: 'change' as const }))];
    },
  });
  const [comments, setComments] = useState<Record<string, string>>({});
  const decide = useMutation({
    mutationFn: ({ row, decision }: { row: Row; decision: 'APPROVED' | 'REJECTED' }) =>
      api(`${row.kind === 'request' ? '/approvals' : '/change-approvals'}/${row.approvalId}/decision`, {
        body: { decision, comments: comments[`${row.kind}-${row.approvalId}`] || undefined },
      }),
    onSuccess: (_d, v) => {
      toast.ok(`${v.row.reference} ${v.decision.toLowerCase()}.`);
      void qc.invalidateQueries({ queryKey: ['approvals'] });
      void qc.invalidateQueries({ queryKey: ['requests'] });
      void qc.invalidateQueries({ queryKey: ['changes'] });
    },
  });
  const pending = (q.data ?? []).filter((a) => !a.decidedAt);
  const done = (q.data ?? []).filter((a) => a.decidedAt);
  return (
    <>
      <PageHead title="Approvals" />
      <Loading q={q} />
      <ErrorBox error={q.error ?? decide.error} />
      <Card title="Waiting for your decision">
        {pending.length === 0 && !q.isLoading && <Empty>Nothing is waiting for your approval.</Empty>}
        <ul className="list">
          {pending.map((a) => {
            const k = `${a.kind}-${a.approvalId}`;
            const link = a.kind === 'request' ? `/requests/${a.requestId}` : `/changes/${a.changeId}`;
            return (
              <li key={k} data-testid="approval-row">
                <div>
                  <strong><Link to={link}>{a.reference}</Link></strong> {a.title}
                  <br /><small className="muted">{a.kind === 'request' ? 'Service request' : 'Change'} - step {a.stepOrder}{a.riskLevel ? ` - risk ${a.riskLevel}` : ''} - {fmtDate(a.createdAt)}</small>
                  <Textarea label="Comments" rows={2} value={comments[k] ?? ''} onChange={(e) => setComments({ ...comments, [k]: e.target.value })} />
                  <div className="actions">
                    <button type="button" className="primary" disabled={decide.isPending} onClick={() => decide.mutate({ row: a, decision: 'APPROVED' })} aria-label={`Approve ${a.reference}`}>Approve</button>
                    <button type="button" className="danger" disabled={decide.isPending} onClick={() => decide.mutate({ row: a, decision: 'REJECTED' })} aria-label={`Reject ${a.reference}`}>Reject</button>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </Card>
      {done.length > 0 && (
        <Card title="Decided">
          <ul className="list">
            {done.map((a) => <li key={`${a.kind}-${a.approvalId}`}><div>{a.reference} {a.title}</div><StatusBadge value={a.decision} /></li>)}
          </ul>
        </Card>
      )}
    </>
  );
}
