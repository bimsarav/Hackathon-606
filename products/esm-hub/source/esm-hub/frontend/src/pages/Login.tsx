import { useState, type FormEvent } from 'react';
import { useAuth } from '../lib/auth';
import { ErrorBox, Input } from '../components/ui';

export function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try { await login(email.trim(), password); } catch (err) { setError(err); } finally { setBusy(false); }
  }

  return (
    <main className="login" id="main">
      <form onSubmit={submit} className="card" aria-labelledby="login-title">
        <h1 id="login-title">Sign in to ESM Hub</h1>
        <ErrorBox error={error} />
        <Input label="Email" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <Input label="Password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        <button type="submit" className="primary" disabled={busy}>{busy ? 'Signing in...' : 'Sign in'}</button>
      </form>
    </main>
  );
}
