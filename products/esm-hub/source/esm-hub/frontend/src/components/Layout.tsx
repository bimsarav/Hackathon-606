import { useState } from 'react';
import { NavLink, Outlet, useLocation, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useAuth, useUser } from '../lib/auth';
import { NAV } from '../lib/roles';

function Bell() {
  const q = useQuery({
    queryKey: ['unread-count'],
    queryFn: () => api<{ unread: number }>('/notifications/unread-count'),
    refetchInterval: 30_000,
  });
  const n = q.data?.unread ?? 0;
  return (
    <Link to="/notifications" className="bell" aria-label={`Notifications, ${n} unread`}>
      <span aria-hidden="true">Bell</span>
      {n > 0 && <span className="bell-count" data-testid="bell-count">{n > 99 ? '99+' : n}</span>}
    </Link>
  );
}

export function Layout() {
  const user = useUser();
  const { logout } = useAuth();
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  const [lastPath, setLastPath] = useState(loc.pathname);
  if (lastPath !== loc.pathname) { setLastPath(loc.pathname); setOpen(false); }
  const items = NAV.filter((n) => n.show(user));

  return (
    <div className="shell">
      <a href="#main" className="skip">Skip to content</a>
      <header className="topbar">
        <button type="button" className="menu-btn" aria-expanded={open} aria-controls="sidenav" onClick={() => setOpen(!open)}>
          Menu
        </button>
        <Link to="/" className="brand">ESM Hub</Link>
        <div className="topbar-right">
          <Bell />
          <span className="who" title={user.email}>{user.name}</span>
          <button type="button" onClick={logout}>Sign out</button>
        </div>
      </header>
      <nav id="sidenav" className={`sidenav ${open ? 'open' : ''}`} aria-label="Main">
        <ul>
          {items.map((n) => (
            <li key={n.to}><NavLink to={n.to} end={n.to === '/'}>{n.label}</NavLink></li>
          ))}
        </ul>
      </nav>
      <main id="main" tabIndex={-1}><Outlet /></main>
    </div>
  );
}
