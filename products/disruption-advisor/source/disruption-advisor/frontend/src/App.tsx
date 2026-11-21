import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api, errorText, type Meta, type Scenario, type ScenarioSummary, type Session, setToken } from "./api";
import { CancelView } from "./CancelView";
import { DelayView } from "./DelayView";
import { Launcher } from "./Launcher";
import { LastWeekPanel } from "./LastWeekPanel";
import { WatchlistView } from "./WatchlistView";
import { utc } from "./format";

const STORAGE_KEY = "disruption-advisor-session";
const OPEN_KEY = "disruption-advisor-open-scenario";
const VIEW_KEY = "disruption-advisor-view";
type View = "scenario" | "watchlist";

function remember(key: string, value: string | null) {
  try {
    if (value) sessionStorage.setItem(key, value);
    else sessionStorage.removeItem(key);
  } catch {
    /* storage unavailable: nothing is remembered across reloads */
  }
}

function loadSession(): Session | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw) as Session;
    return new Date(session.expires_at) > new Date() ? session : null;
  } catch {
    return null;
  }
}

export function App() {
  const [session, setSession] = useState<Session | null>(() => {
    const s = loadSession();
    setToken(s?.token ?? null);
    return s;
  });

  function signIn(s: Session) {
    setToken(s.token);
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    } catch {
      /* storage unavailable: session lasts for this page only */
    }
    setSession(s);
  }

  function signOut() {
    setToken(null);
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
    setSession(null);
  }

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      {session ? <Console session={session} onSignOut={signOut} /> : <Login onSignIn={signIn} />}
    </>
  );
}

function Login({ onSignIn }: { onSignIn: (s: Session) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onSignIn(await api.login(username, password));
    } catch (e: unknown) {
      setError(errorText(e, "Sign-in failed. Check your connection and try again."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main id="main" className="login">
      <div className="login-card">
        <div className="login-brand">
          <img className="brand-tail" src="/brand/air-arabia-tail.svg" alt="" />
          <img className="brand-logo" src="/brand/air-arabia-logo.svg" alt="Air Arabia" />
        </div>
        <p className="eyebrow">Operations Control · Passenger Control Unit</p>
        <h1>Disruption Advisor</h1>
        <p className="muted">Assess a disruption, compare recovery options and protect passengers before the impact spreads.</p>
        <form onSubmit={onSubmit} aria-describedby={error ? "login-error" : undefined}>
          <label htmlFor="username">User name</label>
          <input id="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" value={password}
            onChange={(e) => setPassword(e.target.value)} required />
          {error && (
            <p id="login-error" className="error" role="alert">
              {error}
            </p>
          )}
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </main>
  );
}

type Load = { kind: "idle" } | { kind: "busy"; label: string } | { kind: "error"; message: string };

function Console({ session, onSignOut }: { session: Session; onSignOut: () => void }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [history, setHistory] = useState<ScenarioSummary[]>([]);
  const [load, setLoad] = useState<Load>({ kind: "idle" });
  const [view, setView] = useState<View>(() => {
    try {
      return sessionStorage.getItem(VIEW_KEY) === "watchlist" ? "watchlist" : "scenario";
    } catch {
      return "scenario";
    }
  });
  useEffect(() => remember(VIEW_KEY, view), [view]);

  const refreshHistory = useCallback(() => {
    api.scenarios().then(setHistory).catch(() => setHistory([]));
  }, []);

  useEffect(() => {
    api
      .meta()
      .then(setMeta)
      .catch((e: unknown) => {
        if (e instanceof Error && "problem" in e && (e as { problem: { status: number } }).problem.status === 401) {
          onSignOut();
          return;
        }
        setMetaError(errorText(e, "Could not load the operating data."));
      });
    refreshHistory();
    // Reopen the scenario that was on screen before a page reload, so the slider keeps working.
    let openId: string | null = null;
    try {
      openId = sessionStorage.getItem(OPEN_KEY);
    } catch {
      openId = null;
    }
    if (openId) {
      api.scenario(openId).then(setScenario).catch(() => remember(OPEN_KEY, null));
    }
  }, [onSignOut, refreshHistory]);

  useEffect(() => remember(OPEN_KEY, scenario?.id ?? null), [scenario?.id]);

  async function run(label: string, action: () => Promise<Scenario>) {
    setView("scenario");
    setLoad({ kind: "busy", label });
    try {
      const s = await action();
      setScenario(s);
      setLoad({ kind: "idle" });
      refreshHistory();
    } catch (e: unknown) {
      setLoad({ kind: "error", message: errorText(e, "The analysis failed. Try again.") });
    }
  }

  return (
    <>
      <header className="site-header">
        <span className="brand">
          <img className="brand-tail" src="/brand/air-arabia-tail.svg" alt="" />
          <img className="brand-logo" src="/brand/air-arabia-logo.svg" alt="Air Arabia" />
          <span className="brand-divider" aria-hidden="true" />
          <span className="brand-name">Disruption Advisor</span>
        </span>
        {meta && (
          <span className="header-meta">
            <span className="chip">Ops clock {utc(meta.now_utc)}</span>
            <span className={`chip ${meta.ai_enabled ? "chip-ok" : "chip-warn"}`}>
              {meta.ai_enabled ? `AI explanations: ${meta.ai_model}` : "AI off: template explanations"}
            </span>
            <span className="chip chip-synthetic" title="Loyalty tier, fare family and most special-service codes are synthetic">
              Synthetic fields labelled
            </span>
          </span>
        )}
        <span className="header-user">
          {session.username} · <strong>{session.role}</strong>
          <button type="button" className="link" onClick={onSignOut}>
            Sign out
          </button>
        </span>
      </header>
      <div className="layout">
        <aside aria-label="Start a scenario">
          {metaError && (
            <p className="error" role="alert">
              {metaError}
            </p>
          )}
          {view === "watchlist" && <LastWeekPanel />}
          {/* Hidden, not unmounted, on the 7-day view: the slider and suggestions keep their state. */}
          <div hidden={view === "watchlist"}>
            {meta && (
              <Launcher
                meta={meta}
                busy={load.kind === "busy"}
                active={scenario && scenario.kind === "DELAY" && scenario.delay_minutes
                  ? { flightId: scenario.flight_id, flightNumber: scenario.result.flight.flight_number, delay: scenario.delay_minutes }
                  : null}
                onDelay={(flightId, delay) =>
                  run(`Analysing a ${delay}-minute delay…`, () =>
                    api.createScenario({ kind: "DELAY", flight_id: flightId, delay_minutes: delay, weights: meta.default_weights }),
                  )
                }
                onCancel={(flightId) =>
                  run("Ranking passengers and rebooking…", () =>
                    api.createScenario({ kind: "CANCEL", flight_id: flightId, weights: meta.default_weights }),
                  )
                }
              />
            )}
            <section className="history" aria-labelledby="history-title">
              <h2 id="history-title">Recent scenarios</h2>
              {history.length === 0 ? (
                <p className="muted">None yet.</p>
              ) : (
                <ul>
                  {history.map((h) => (
                    <li key={h.id}>
                      <button type="button" className="link" onClick={() => run("Opening scenario…", () => api.scenario(h.id))}>
                        {h.kind === "DELAY" ? `Delay +${h.delay_minutes} min` : "Cancellation"} · {h.flight_id.split("_")[0]}
                      </button>
                      <span className="muted small">
                        {" "}
                        {h.created_by}, {utc(h.created_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </aside>
        <main id="main" aria-live="polite" aria-busy={load.kind === "busy"}>
          <nav className="tabs view-tabs" aria-label="Views">
            <button type="button" className={`tab ${view === "scenario" ? "active" : ""}`} aria-pressed={view === "scenario"}
              onClick={() => setView("scenario")}>
              Scenario
            </button>
            <button type="button" className={`tab ${view === "watchlist" ? "active" : ""}`} aria-pressed={view === "watchlist"}
              onClick={() => setView("watchlist")}>
              Delay watchlist (7 days)
            </button>
          </nav>
          {view === "watchlist" && meta && (
            <WatchlistView
              busy={load.kind === "busy"}
              onAnalyse={(flightId, delay) =>
                run(`Analysing a ${delay}-minute delay…`, () =>
                  api.createScenario({ kind: "DELAY", flight_id: flightId, delay_minutes: delay, weights: meta.default_weights }),
                )
              }
            />
          )}
          {view === "scenario" && load.kind === "busy" && <p className="status">{load.label}</p>}
          {view === "scenario" && load.kind === "error" && (
            <p className="error" role="alert">
              {load.message}
            </p>
          )}
          {view === "scenario" && !scenario && load.kind !== "busy" && (
            <section className="empty">
              <h1>Start with a disruption</h1>
              <p>
                Pick a suggested flight on the left, or search for any flight. <strong>Delay</strong> shows the knock-on
                effect along the aircraft rotation and compares recovery options. <strong>Cancellation</strong> ranks the
                affected passengers and rebooks them within the seats that are actually available.
              </p>
              <p className="muted">Every recommendation needs a person to approve it. Nothing is changed in airline systems.</p>
            </section>
          )}
          {view === "scenario" && scenario && meta && scenario.result.type === "DELAY" && (
            <DelayView scenario={scenario} result={scenario.result} meta={meta} onUpdate={setScenario} />
          )}
          {view === "scenario" && scenario && meta && scenario.result.type === "CANCEL" && (
            <CancelView scenario={scenario} result={scenario.result} meta={meta} onUpdate={setScenario} />
          )}
        </main>
      </div>
    </>
  );
}
