import { type FormEvent, useCallback, useEffect, useState } from "react";
import { AgentRunsList, AgentRunView, agentStartError } from "./AgentRunView";
import {
  type AgentRunRequest,
  api,
  errorText,
  type Meta,
  type Scenario,
  type ScenarioSummary,
  type Session,
  setToken,
} from "./api";
import { CancelView } from "./CancelView";
import { CascadePanel } from "./CascadePanel";
import { DelayView } from "./DelayView";
import { Launcher } from "./Launcher";
import { ModelCardView } from "./ModelCardView";
import { RewardPanel } from "./RewardPanel";
import { TestDataPanel } from "./TestDataPanel";
import { WatchlistView } from "./WatchlistView";

const STORAGE_KEY = "disruption-advisor-session";
const OPEN_KEY = "disruption-advisor-open-scenario";
const VIEW_KEY = "disruption-advisor-view";
const AGENT_KEY = "disruption-advisor-agent-run";
type View = "delay" | "cancel" | "agent" | "watchlist" | "model" | "testdata" | "recent";
const VIEWS: View[] = ["delay", "cancel", "agent", "watchlist", "model", "testdata", "recent"];
/** Views only the evaluator role sees (the server refuses the others as well). */
const EVALUATOR_VIEWS: View[] = ["model", "testdata"];

function recall(key: string): string | null {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function remember(key: string, value: string | null) {
  try {
    if (value) sessionStorage.setItem(key, value);
    else sessionStorage.removeItem(key);
  } catch {
    /* storage unavailable */
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
      /* ignore */
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
        <div className="login-brand brand">
          <span className="brand-icon-wrap">
            <img src="/brand/air-arabia-tail.svg" alt="Air Arabia" />
          </span>
          <span className="brand-name">aeroRecovery</span>
        </div>
        <p className="eyebrow">Operations Control · Passenger Control Unit</p>
        <h1>aeroRecovery</h1>
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

const VIEW_LABEL: Record<View, string> = {
  delay: "Flight Delay",
  cancel: "Cancellation",
  agent: "Predict the Flight Delay",
  watchlist: "Delay Watchlist",
  model: "Model Card",
  testdata: "Test Data",
  recent: "Recent Searches",
};
const VIEW_SECTION: Partial<Record<View, string>> = {
  delay: "Analyze", cancel: "Analyze", agent: "Analyze",
  watchlist: "Monitor",
  model: "Reference", testdata: "Reference",
};

function Breadcrumb({ view, scenario, onView }: { view: View; scenario: Scenario | null; onView: (v: View) => void }) {
  const section = VIEW_SECTION[view];
  const viewLabel = VIEW_LABEL[view];
  const flightLabel = scenario
    ? scenario.result.type === "DELAY"
      ? `${scenario.result.flight.flight_number} · +${scenario.delay_minutes}m`
      : `${scenario.result.flight.flight_number} · Cancellation`
    : null;
  return (
    <nav className="breadcrumb" aria-label="Breadcrumb">
      <span className="bc-item bc-home" onClick={() => onView(view)}>aeroRecovery</span>
      {section && <><span className="bc-sep">›</span><span className="bc-item bc-section">{section}</span></>}
      <span className="bc-sep">›</span>
      <span className="bc-item bc-view">{viewLabel}</span>
      {flightLabel && <><span className="bc-sep">›</span><span className="bc-item bc-flight">{flightLabel}</span></>}
    </nav>
  );
}

function NavItem({ label, icon, active, onClick }: { label: string; icon: string; active: boolean; onClick: () => void }) {
  return (
    <button type="button" className={`nav-item${active ? " active" : ""}`} onClick={onClick} aria-current={active ? "page" : undefined}>
      <span className="nav-icon" aria-hidden="true">{icon}</span>
      {label}
    </button>
  );
}

function Console({ session, onSignOut }: { session: Session; onSignOut: () => void }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [history, setHistory] = useState<ScenarioSummary[]>([]);
  const [load, setLoad] = useState<Load>({ kind: "idle" });
  const [delaySubmitted, setDelaySubmitted] = useState(false);
  const [cancelSubmitted, setCancelSubmitted] = useState(false);
  const isEvaluator = session.role === "EVALUATOR";
  const [view, setView] = useState<View>(() => {
    const saved = recall(VIEW_KEY) as View | null;
    return saved && VIEWS.includes(saved) && (isEvaluator || !EVALUATOR_VIEWS.includes(saved)) ? saved : "delay";
  });
  useEffect(() => remember(VIEW_KEY, view), [view]);
  const [agentRunId, setAgentRunId] = useState<string | null>(() => recall(AGENT_KEY));
  const [agentStart, setAgentStart] = useState<Load>({ kind: "idle" });
  const [agentStatus, setAgentStatus] = useState<string | null>(null);
  useEffect(() => remember(AGENT_KEY, agentRunId), [agentRunId]);

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

  async function run(targetView: "delay" | "cancel", label: string, action: () => Promise<Scenario>) {
    setView(targetView);
    setLoad({ kind: "busy", label });
    try {
      const s = await action();
      setScenario(s);
      if (targetView === "delay") setDelaySubmitted(true);
      if (targetView === "cancel") setCancelSubmitted(true);
      setLoad({ kind: "idle" });
      refreshHistory();
    } catch (e: unknown) {
      setLoad({ kind: "error", message: errorText(e, "The analysis failed. Try again.") });
    }
  }

  async function askAgent(request: AgentRunRequest) {
    setView("agent");
    setAgentStart({ kind: "busy", label: "Starting the agent…" });
    try {
      const started = await api.startAgent({ ...request, note: request.note ?? "" });
      setAgentRunId(started.id);
      setAgentStart({ kind: "idle" });
    } catch (e: unknown) {
      setAgentStart({ kind: "error", message: agentStartError(e) });
    }
  }

  const busy = load.kind === "busy" || agentStart.kind === "busy";

  const delayActive = scenario && scenario.kind === "DELAY" && scenario.delay_minutes
    ? { flightId: scenario.flight_id, flightNumber: scenario.result.flight.flight_number, delay: scenario.delay_minutes }
    : null;

  return (
    <>
      <header className="site-header">
        <span className="brand">
          <span className="brand-icon-wrap">
            <img src="/brand/air-arabia-tail.svg" alt="Air Arabia" />
          </span>
          <span className="brand-name">aeroRecovery</span>
        </span>
        <span className="header-user">
          <span className="user-avatar" aria-hidden="true">
            {session.username.charAt(0).toUpperCase()}
          </span>
          <span className="user-name">{session.username}</span>
          <button type="button" className="link sign-out-btn" onClick={onSignOut}>
            Sign out
          </button>
        </span>
      </header>

      <div className="layout">
        <aside className="nav-sidebar" aria-label="Navigation">
          {metaError && <p className="error small" role="alert">{metaError}</p>}

          <nav>
            <div className="nav-section">
              <p className="nav-section-label">Analyze</p>
              <NavItem label="Flight Delay" icon="↑" active={view === "delay"} onClick={() => setView("delay")} />
              <NavItem label="Cancellation" icon="✕" active={view === "cancel"} onClick={() => setView("cancel")} />
              <NavItem label="Predict the Flight Delay" icon="◎" active={view === "agent"} onClick={() => setView("agent")} />
            </div>
            <div className="nav-section">
              <p className="nav-section-label">Monitor</p>
              <NavItem label="Delay Watchlist" icon="◉" active={view === "watchlist"} onClick={() => setView("watchlist")} />
            </div>
            {isEvaluator && (
              <div className="nav-section">
                <p className="nav-section-label">Reference</p>
                <NavItem label="Model Card" icon="☰" active={view === "model"} onClick={() => setView("model")} />
                <NavItem label="Test data" icon="⇪" active={view === "testdata"} onClick={() => setView("testdata")} />
              </div>
            )}
          </nav>

          {history.length > 0 && (
            <div className="nav-section">
              <NavItem label="Recent Searches" icon="🕐" active={view === "recent"} onClick={() => setView("recent")} />
            </div>
          )}
        </aside>

        <main id="main" aria-live="polite" aria-busy={load.kind === "busy"}>
          <Breadcrumb view={view} scenario={scenario} onView={setView} />

          {/* ── Flight Delay ─────────────────────────────── */}
          {view === "delay" && (
            <>
              {load.kind === "busy" && <p className="status">{load.label}</p>}
              {load.kind === "error" && <p className="error" role="alert">{load.message}</p>}
              {meta && (
                <Launcher
                  key="delay"
                  meta={meta}
                  busy={busy}
                  defaultTab="DELAY"
                  hideTabNav
                  active={delayActive}
                  onDelay={(flightId, delay) =>
                    run("delay", `Analysing a ${delay}-minute delay…`, () =>
                      api.createScenario({ kind: "DELAY", flight_id: flightId, delay_minutes: delay, weights: meta.default_weights })
                    )
                  }
                  onCancel={(flightId) =>
                    run("cancel", "Ranking passengers and rebooking…", () =>
                      api.createScenario({ kind: "CANCEL", flight_id: flightId, weights: meta.default_weights })
                    )
                  }
                  onAgent={askAgent}
                />
              )}
              {!delaySubmitted && load.kind !== "busy" && (
                <section className="empty">
                  <h1>Flight Delay Analysis</h1>
                  <p>Select a suggested flight above, or search by flight number, airport or aircraft tail. The engine maps the knock-on effect along the full rotation and compares every recovery option by cost.</p>
                  <p className="muted">Every recommendation needs a person to approve it before anything changes in airline systems.</p>
                </section>
              )}
              {delaySubmitted && scenario && meta && scenario.result.type === "DELAY" && (
                <DelayView scenario={scenario} result={scenario.result} meta={meta} onUpdate={setScenario} />
              )}
            </>
          )}

          {/* ── Cancellation ─────────────────────────────── */}
          {view === "cancel" && (
            <>
              {load.kind === "busy" && <p className="status">{load.label}</p>}
              {load.kind === "error" && <p className="error" role="alert">{load.message}</p>}
              {meta && (
                <Launcher
                  key="cancel"
                  meta={meta}
                  busy={busy}
                  defaultTab="CANCEL"
                  hideTabNav
                  active={null}
                  onDelay={(flightId, delay) =>
                    run("delay", `Analysing a ${delay}-minute delay…`, () =>
                      api.createScenario({ kind: "DELAY", flight_id: flightId, delay_minutes: delay, weights: meta.default_weights })
                    )
                  }
                  onCancel={(flightId) =>
                    run("cancel", "Ranking passengers and rebooking…", () =>
                      api.createScenario({ kind: "CANCEL", flight_id: flightId, weights: meta.default_weights })
                    )
                  }
                  onAgent={askAgent}
                />
              )}
              {!cancelSubmitted && load.kind !== "busy" && (
                <section className="empty">
                  <h1>Cancellation Analysis</h1>
                  <p>Select a flight to cancel. The engine ranks all affected passengers by tier and urgency, then rebooks them against available seats on alternative flights.</p>
                  <p className="muted">Every recommendation needs a person to approve it before anything changes in airline systems.</p>
                </section>
              )}
              {cancelSubmitted && scenario && meta && scenario.result.type === "CANCEL" && (
                <CancelView scenario={scenario} result={scenario.result} meta={meta} onUpdate={setScenario} />
              )}
            </>
          )}

          {/* ── Agent ─────────────────────────────────────── */}
          {view === "agent" && (
            <>
              {agentStart.kind === "busy" && <p className="status">{agentStart.label}</p>}
              {agentStart.kind === "error" && <p className="error" role="alert">{agentStart.message}</p>}
              {meta && (
                <Launcher
                  key="agent"
                  meta={meta}
                  busy={busy}
                  defaultTab="AGENT"
                  hideTabNav
                  active={null}
                  onDelay={(flightId, delay) =>
                    run("delay", `Analysing a ${delay}-minute delay…`, () =>
                      api.createScenario({ kind: "DELAY", flight_id: flightId, delay_minutes: delay, weights: meta.default_weights })
                    )
                  }
                  onCancel={(flightId) =>
                    run("cancel", "Ranking passengers and rebooking…", () =>
                      api.createScenario({ kind: "CANCEL", flight_id: flightId, weights: meta.default_weights })
                    )
                  }
                  onAgent={askAgent}
                />
              )}
              {agentRunId ? (
                <AgentRunView
                  runId={agentRunId}
                  onRetry={askAgent}
                  onStatus={setAgentStatus}
                  onOpenScenario={(id) => run("delay", "Opening the agent's scenario…", () => api.scenario(id))}
                />
              ) : (
                agentStart.kind === "idle" && (
                  <section className="empty">
                    <h1>Agent Console</h1>
                    <p>Select a flight above and ask the agent to investigate it. The agent uses the recovery engine, shows each reasoning step and recommends one option — you review and approve or override it.</p>
                  </section>
                )
              )}
              <AgentRunsList
                refreshKey={`${agentRunId}:${agentStatus}`}
                onOpen={(id) => { setAgentStart({ kind: "idle" }); setAgentRunId(id); }}
              />
            </>
          )}

          {/* ── Delay Watchlist ───────────────────────────── */}
          {view === "watchlist" && (
            <>
              {scenario && <RewardPanel scenario={scenario} />}
              <CascadePanel />
              {meta && (
                <WatchlistView
                  busy={busy}
                  onAnalyse={(flightId, delay) =>
                    run("delay", `Analysing a ${delay}-minute delay…`, () =>
                      api.createScenario({ kind: "DELAY", flight_id: flightId, delay_minutes: delay, weights: meta.default_weights })
                    )
                  }
                  onAgent={(flightId, delay) => askAgent({ flight_id: flightId, delay_minutes: delay })}
                />
              )}
            </>
          )}

          {/* ── Model Card ────────────────────────────────── */}
          {isEvaluator && view === "model" && <ModelCardView />}

          {/* ── Test data (evaluator) ─────────────────────── */}
          {isEvaluator && view === "testdata" && <TestDataPanel />}

          {/* ── Recent Searches ───────────────────────────── */}
          {view === "recent" && (
            <section>
              <h1>Recent Searches</h1>
              <p className="muted">Your last {history.length} scenario{history.length !== 1 ? "s" : ""}. Click one to reload it.</p>
              <ul className="recent-list">
                {history.map((h) => (
                  <li key={h.id}>
                    <button
                      type="button"
                      className="recent-item"
                      disabled={load.kind === "busy"}
                      onClick={() => run(
                        h.kind === "DELAY" ? "delay" : "cancel",
                        "Opening scenario…",
                        () => api.scenario(h.id)
                      )}
                    >
                      <span className={`recent-badge ${h.kind === "DELAY" ? "recent-badge-delay" : "recent-badge-cancel"}`}>
                        {h.kind === "DELAY" ? "Flight Delay" : "Cancellation"}
                      </span>
                      <span className="recent-flight">{h.flight_id.split("_")[0]}</span>
                      <span className="recent-kind muted small">{h.kind === "DELAY" ? "Delay scenario" : "Cancellation"}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

        </main>
      </div>
    </>
  );
}
