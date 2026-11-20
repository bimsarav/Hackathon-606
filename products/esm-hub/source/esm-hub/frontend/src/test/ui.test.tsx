import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BarChart, ErrorBox } from '../components/ui';
import { ApiError } from '../lib/api';
import { Login } from '../pages/Login';
import { Layout } from '../components/Layout';
import { AuthProvider } from '../lib/auth';
import { ToastProvider, useToast } from '../components/Toast';
import { setToken } from '../lib/api';
import { Routes, Route } from 'react-router-dom';

function jwt(payload: object): string {
  const b64 = (o: object) => btoa(JSON.stringify(o)).replace(/=+$/, '');
  return `${b64({})}.${b64(payload)}.s`;
}

function wrap(ui: React.ReactNode, path = '/') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><MemoryRouter initialEntries={[path]}><ToastProvider><AuthProvider>{ui}</AuthProvider></ToastProvider></MemoryRouter></QueryClientProvider>,
  );
}

describe('ErrorBox', () => {
  it('shows title, detail and request id', () => {
    render(<ErrorBox error={new ApiError(422, { title: 'Invalid', detail: 'Nope', requestId: 'abc-123' })} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid');
    expect(screen.getByRole('alert')).toHaveTextContent('abc-123');
  });
});

describe('BarChart', () => {
  it('renders one row per value', () => {
    render(<BarChart title="By month" rows={[{ label: '2026-01', value: 3 }, { label: '2026-02', value: 6 }]} />);
    expect(screen.getByText('By month')).toBeInTheDocument();
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
  });
});

describe('Login', () => {
  it('has labelled fields and shows server errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ title: 'Unauthorized', detail: 'Invalid credentials', requestId: 'r9' }), { status: 401 })));
    wrap(<Login />);
    await userEvent.type(screen.getByLabelText('Email'), 'a@b.test');
    await userEvent.type(screen.getByLabelText('Password'), 'secret');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid credentials');
    expect(screen.getByRole('alert')).toHaveTextContent('r9');
    vi.unstubAllGlobals();
  });
  it('stores the token in sessionStorage on success', async () => {
    const t = jwt({ sub: '1', roles: ['EMPLOYEE'], name: 'P', email: 'p@x.test', exp: 4102444800 });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ accessToken: t, tokenType: 'Bearer', expiresIn: 3600 }), { status: 200 })));
    wrap(<Login />);
    await userEvent.type(screen.getByLabelText('Email'), 'p@x.test');
    await userEvent.type(screen.getByLabelText('Password'), 'pw');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    await vi.waitFor(() => expect(sessionStorage.getItem('esm.token')).toBe(t));
    vi.unstubAllGlobals();
  });
});

describe('Layout', () => {
  function shell(roles: string[]) {
    setToken(jwt({ sub: '1', roles, name: 'Test User', email: 't@x.test', exp: 4102444800 }));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ unread: 2 }), { status: 200 })));
    wrap(<Routes><Route element={<Layout />}><Route index element={<p>home</p>} /></Route></Routes>);
  }
  it('gives an employee no admin navigation, with landmarks', async () => {
    shell(['EMPLOYEE']);
    expect(screen.getByRole('navigation', { name: 'Main' })).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Admin' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Audit' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Incidents' })).toBeInTheDocument();
    expect(await screen.findByTestId('bell-count')).toHaveTextContent('2');
    vi.unstubAllGlobals();
  });
  it('shows admin navigation to an admin', () => {
    shell(['ADMIN']);
    expect(screen.getByRole('link', { name: 'Admin' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Audit' })).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});

describe('Toast', () => {
  function Demo() { const t = useToast(); return <button onClick={() => t.ok('Saved!')}>go</button>; }
  it('announces through a polite live region', async () => {
    render(<ToastProvider><Demo /></ToastProvider>);
    await userEvent.click(screen.getByText('go'));
    const region = screen.getByRole('status');
    expect(region).toHaveAttribute('aria-live', 'polite');
    expect(region).toHaveTextContent('Saved!');
  });
});
