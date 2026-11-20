import { useState, type FormEvent } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useToast } from '../components/Toast';
import { Card, ErrorBox, Input, PageHead } from '../components/ui';
import { human } from '../lib/format';

export function Account() {
  const toast = useToast();
  const me = useQuery({ queryKey: ['me'], queryFn: () => api<{ name: string; email: string; roles: string[] }>('/auth/me') });
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [mismatch, setMismatch] = useState(false);
  const m = useMutation({
    mutationFn: () => api('/auth/password', { body: { currentPassword: current, newPassword: next } }),
    onSuccess: () => { toast.ok('Password changed.'); setCurrent(''); setNext(''); setConfirm(''); },
  });
  function submit(e: FormEvent) {
    e.preventDefault();
    if (next !== confirm) { setMismatch(true); return; }
    setMismatch(false);
    m.mutate();
  }
  return (
    <>
      <PageHead title="My account" />
      <Card title="Profile">
        <dl className="kv">
          <dt>Name</dt><dd>{me.data?.name}</dd>
          <dt>Email</dt><dd>{me.data?.email}</dd>
          <dt>Roles</dt><dd>{me.data?.roles.map(human).join(', ')}</dd>
        </dl>
      </Card>
      <Card title="Change password">
        <form onSubmit={submit} className="form">
          <ErrorBox error={m.error} />
          {mismatch && <div className="error" role="alert">The new passwords do not match.</div>}
          <Input label="Current password" type="password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} />
          <Input label="New password" type="password" autoComplete="new-password" required minLength={8} value={next} onChange={(e) => setNext(e.target.value)} />
          <Input label="Confirm new password" type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          <button type="submit" className="primary" disabled={m.isPending}>Change password</button>
        </form>
      </Card>
    </>
  );
}
