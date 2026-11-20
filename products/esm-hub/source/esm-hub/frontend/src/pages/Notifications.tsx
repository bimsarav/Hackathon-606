import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { fmtDate } from '../lib/format';
import type { Notification, Page } from '../lib/types';
import { Badge, Empty, ErrorBox, Loading, PageHead, Pager } from '../components/ui';

/** Map an API link such as /incidents/12 to a SPA route. */
function route(n: Notification): string | null {
  const l = n.link;
  if (l && l.startsWith('/') && !l.startsWith('//')) return l.replace(/^\/api\/v1/, '');
  return null;
}

export function Notifications() {
  const qc = useQueryClient();
  const [unread, setUnread] = useState(false);
  const [page, setPage] = useState(1);
  const q = useQuery({
    queryKey: ['notifications', unread, page],
    queryFn: () => api<Page<Notification>>('/notifications', { query: { unread, page, size: 20 } }),
  });
  const refresh = () => { void qc.invalidateQueries({ queryKey: ['notifications'] }); void qc.invalidateQueries({ queryKey: ['unread-count'] }); };
  const read = useMutation({ mutationFn: (id: number) => api(`/notifications/${id}/read`, { method: 'POST' }), onSuccess: refresh });
  const readAll = useMutation({ mutationFn: () => api('/notifications/read-all', { method: 'POST' }), onSuccess: refresh });

  return (
    <>
      <PageHead title="Notifications">
        <label className="inline"><input type="checkbox" checked={unread} onChange={(e) => { setUnread(e.target.checked); setPage(1); }} /> Unread only</label>
        <button type="button" onClick={() => readAll.mutate()} disabled={readAll.isPending}>Mark all read</button>
      </PageHead>
      <Loading q={q} />
      <ErrorBox error={q.error ?? read.error ?? readAll.error} />
      {q.data?.items.length === 0 && <Empty>No notifications.</Empty>}
      <ul className="list">
        {q.data?.items.map((n) => {
          const to = route(n);
          return (
            <li key={n.id} className={n.readAt ? '' : 'unread'}>
              <div>
                <strong>{to ? <Link to={to}>{n.subject}</Link> : n.subject}</strong>{' '}
                {!n.readAt && <Badge tone="info">New</Badge>}
                {n.body && <p>{n.body}</p>}
                <small className="muted">{fmtDate(n.createdAt)}{n.reference ? ` - ${n.reference}` : ''}</small>
              </div>
              {!n.readAt && <button type="button" onClick={() => read.mutate(n.id)}>Mark read</button>}
            </li>
          );
        })}
      </ul>
      <Pager page={page} onPage={setPage} data={q.data} />
    </>
  );
}
