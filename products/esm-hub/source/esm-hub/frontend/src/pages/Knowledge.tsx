import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useUser } from '../lib/auth';
import { hasRole, KB_AUTHOR_ROLES, R } from '../lib/roles';
import { fmtDay, human } from '../lib/format';
import { useReference } from '../lib/hooks';
import type { Article, Page } from '../lib/types';
import { useToast } from '../components/Toast';
import { Card, Empty, ErrorBox, Input, Loading, PageHead, Pager, Select, StatusBadge, Textarea } from '../components/ui';

const FLOW: Record<string, string[]> = { DRAFT: ['UNDER_REVIEW'], UNDER_REVIEW: ['PUBLISHED', 'DRAFT'], PUBLISHED: ['RETIRED', 'DRAFT'], RETIRED: ['DRAFT'] };

export function KbList() {
  const user = useUser();
  const author = hasRole(user, ...KB_AUTHOR_ROLES);
  const [text, setText] = useState('');
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [page, setPage] = useState(1);
  const ref = useReference();
  const [creating, setCreating] = useState(false);
  const list = useQuery({ queryKey: ['kb', q, status, categoryId, page], queryFn: () => api<Page<Article>>('/kb/articles', { query: { q, status, categoryId, page, size: 20 } }) });
  return (
    <>
      <PageHead title="Knowledge base">
        {author && <button type="button" className="primary" onClick={() => setCreating(!creating)} aria-expanded={creating}>New article</button>}
      </PageHead>
      {creating && <Card title="New article"><ArticleForm onSaved={() => setCreating(false)} /></Card>}
      <form className="filters" role="search" onSubmit={(e) => { e.preventDefault(); setQ(text); setPage(1); }}>
        <Input label="Search articles" type="search" value={text} onChange={(e) => setText(e.target.value)} placeholder="e.g. VPN, password reset" />
        <Select label="Category" value={categoryId} onChange={(e) => { setCategoryId(e.target.value); setPage(1); }} blank="All categories" options={(ref.data?.categories ?? []).map((c) => ({ value: c.categoryId, label: c.name }))} />
        {author && <Select label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} blank="Published" options={['DRAFT', 'UNDER_REVIEW', 'PUBLISHED', 'RETIRED'].map((s) => ({ value: s, label: human(s) }))} />}
        <button type="submit">Search</button>
      </form>
      <Loading q={list} />
      <ErrorBox error={list.error} />
      {list.data?.items.length === 0 && <Empty>No articles found.</Empty>}
      <ul className="list articles">
        {list.data?.items.map((a) => (
          <li key={a.articleId}>
            <div>
              <h2><Link to={`/knowledge/${a.articleId}`}>{a.title}</Link></h2>
              {a.snippet && <p>{a.snippet}</p>}
              <small className="muted">{a.authorName} - {fmtDay(a.publishedAt ?? a.updatedAt)} - {a.viewCount} views</small>
            </div>
            {a.status !== 'PUBLISHED' && <StatusBadge value={a.status} />}
          </li>
        ))}
      </ul>
      <Pager page={page} onPage={setPage} data={list.data} />
    </>
  );
}

function ArticleForm({ initial, onSaved }: { initial?: Article; onSaved: (a: Article) => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const ref = useReference();
  const [title, setTitle] = useState(initial?.title ?? '');
  const [body, setBody] = useState(initial?.body ?? '');
  const [categoryId, setCategoryId] = useState(String(initial?.categoryId ?? ''));
  const m = useMutation({
    mutationFn: () => api<Article>(initial ? `/kb/articles/${initial.articleId}` : '/kb/articles', {
      method: initial ? 'PATCH' : 'POST', body: { title, body, categoryId: categoryId ? Number(categoryId) : undefined },
    }),
    onSuccess: (a) => { toast.ok('Article saved.'); void qc.invalidateQueries({ queryKey: ['kb'] }); void qc.invalidateQueries({ queryKey: ['article'] }); onSaved(a); },
  });
  return (
    <form className="form" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <ErrorBox error={m.error} />
      <Input label="Title" required minLength={3} maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />
      <Select label="Category" value={categoryId} onChange={(e) => setCategoryId(e.target.value)} blank="None" options={(ref.data?.categories ?? []).map((c) => ({ value: c.categoryId, label: c.name }))} />
      <Textarea label="Body" required minLength={10} rows={12} value={body} onChange={(e) => setBody(e.target.value)} hint="Plain text. Line breaks are preserved." />
      <button type="submit" className="primary" disabled={m.isPending}>Save article</button>
    </form>
  );
}

export function KbArticle() {
  const { id } = useParams();
  const nav = useNavigate();
  const user = useUser();
  const qc = useQueryClient();
  const toast = useToast();
  const q = useQuery({ queryKey: ['article', id], queryFn: () => api<Article>(`/kb/articles/${id}`) });
  const [editing, setEditing] = useState(false);
  const [comment, setComment] = useState('');
  const [voted, setVoted] = useState(false);
  const a = q.data;
  const editor = hasRole(user, R.KE);
  const isAuthor = !!a && String(a.authorId) === user.sub;
  const canEdit = hasRole(user, ...KB_AUTHOR_ROLES) && (editor || isAuthor);
  const status = useMutation({
    mutationFn: (s: string) => api(`/kb/articles/${id}/status`, { body: { status: s } }),
    onSuccess: () => { toast.ok('Article status updated.'); void qc.invalidateQueries({ queryKey: ['article', id] }); void qc.invalidateQueries({ queryKey: ['kb'] }); },
  });
  const feedback = useMutation({
    mutationFn: (helpful: boolean) => api(`/kb/articles/${id}/feedback`, { body: { helpful, comment: comment || undefined } }),
    onSuccess: () => { toast.ok('Thanks for your feedback.'); setVoted(true); setComment(''); void qc.invalidateQueries({ queryKey: ['article', id] }); },
  });
  if (q.isLoading) return <Loading />;
  if (!a) return <ErrorBox error={q.error} />;
  return (
    <>
      <PageHead title={a.title}><button type="button" onClick={() => nav(-1)}>Back</button></PageHead>
      <ErrorBox error={status.error ?? feedback.error} />
      <article className="card article">
        <p className="muted"><StatusBadge value={a.status} /> By {a.authorName} - {fmtDay(a.publishedAt ?? a.updatedAt)} - {a.viewCount} views</p>
        <div className="pre article-body">{a.body}</div>
      </article>
      {a.status === 'PUBLISHED' && (
        <Card title="Was this article helpful?">
          {voted ? <p>Thank you, your feedback was recorded.</p> : (
            <form className="form" onSubmit={(e) => e.preventDefault()}>
              <Textarea label="Comment (optional)" rows={2} maxLength={500} value={comment} onChange={(e) => setComment(e.target.value)} />
              <div className="actions">
                <button type="button" onClick={() => feedback.mutate(true)} disabled={feedback.isPending}>Helpful</button>
                <button type="button" onClick={() => feedback.mutate(false)} disabled={feedback.isPending}>Not helpful</button>
              </div>
            </form>
          )}
          <small className="muted">{a.helpfulCount} found this helpful, {a.notHelpfulCount} did not.</small>
        </Card>
      )}
      {canEdit && (
        <Card title="Authoring">
          <div className="actions">
            {(FLOW[a.status] ?? [])
              .filter((s) => s !== 'PUBLISHED' || editor)
              .map((s) => <button key={s} type="button" disabled={status.isPending} onClick={() => status.mutate(s)}>{s === 'UNDER_REVIEW' ? 'Submit for review' : s === 'PUBLISHED' ? 'Publish' : s === 'DRAFT' ? 'Return to draft' : 'Retire'}</button>)}
            <button type="button" onClick={() => setEditing(!editing)} aria-expanded={editing}>Edit article</button>
          </div>
          {editing && <ArticleForm initial={a} onSaved={() => setEditing(false)} />}
        </Card>
      )}
    </>
  );
}
