import { type FormEvent, useEffect, useState } from "react";
import {
  type AgentRunRequest,
  api,
  type CancelPreset,
  type DelayPreset,
  errorText,
  type FlightRow,
  type Meta,
  STRATEGY_KEYS,
  STRATEGY_LABEL,
  type StrategyKey,
} from "./api";
import { CarrierTail } from "./CarrierTail";
import { utc } from "./format";

interface Props {
  meta: Meta;
  busy: boolean;
  /** The delay scenario on screen, if any: moving the slider re-runs it. */
  active?: { flightId: string; flightNumber: string; delay: number } | null;
  onDelay: (flightId: string, delay: number) => void;
  onCancel: (flightId: string) => void;
  /** Phase 3: hands the flight to the agent (it recommends; a person approves). */
  onAgent?: (request: AgentRunRequest) => void;
  /** Pre-select a tab (Launcher remounts when view changes via key prop). */
  defaultTab?: Tab;
  /** Hide the tab switcher — when the caller's nav already sets the mode. */
  hideTabNav?: boolean;
}

type Tab = "DELAY" | "CANCEL" | "AGENT";
const AGENT_DELAYS = [30, 60, 90, 120, 150, 180, 240, 300, 360, 480];

/** Scenario launcher: suggested flights from the data (UC5 example scenario) or any flight by search. */
const PAGE_SIZES = [5, 10, 15] as const;

function Paginator({
  total, page, pageSize, onPage, onPageSize,
}: { total: number; page: number; pageSize: number; onPage: (p: number) => void; onPageSize: (n: number) => void }) {
  const totalPages = Math.ceil(total / pageSize);
  if (total <= PAGE_SIZES[0]) return null;
  const start = page * pageSize + 1;
  const end = Math.min((page + 1) * pageSize, total);
  return (
    <div className="paginator">
      <span className="paginator-info">{start}–{end} of {total}</span>
      <button type="button" className="paginator-btn" disabled={page === 0} onClick={() => onPage(page - 1)}>‹</button>
      <button type="button" className="paginator-btn" disabled={page >= totalPages - 1} onClick={() => onPage(page + 1)}>›</button>
      <select className="paginator-size" value={pageSize} onChange={(e) => { onPageSize(Number(e.target.value)); onPage(0); }}>
        {PAGE_SIZES.map((s) => <option key={s} value={s}>{s} per page</option>)}
      </select>
    </div>
  );
}

export function Launcher({ busy, active, onDelay, onCancel, onAgent, defaultTab, hideTabNav }: Props) {
  const [tab, setTab] = useState<Tab>(defaultTab ?? "DELAY");
  const [presets, setPresets] = useState<{ delay: DelayPreset[]; cancel: CancelPreset[] } | null>(null);
  const [presetError, setPresetError] = useState<string | null>(null);
  const [delay, setDelay] = useState(150);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<FlightRow[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [agentDelay, setAgentDelay] = useState<number | null>(null);
  const [agentStrategy, setAgentStrategy] = useState<StrategyKey | null>(null);
  const [agentNote, setAgentNote] = useState("");
  const [searchPage, setSearchPage] = useState(0);
  const [searchPageSize, setSearchPageSize] = useState<number>(5);
  const [presetPage, setPresetPage] = useState(0);
  const [presetPageSize, setPresetPageSize] = useState<number>(5);

  // Keep the slider in step with the scenario on screen (e.g. one reopened from history).
  useEffect(() => {
    if (active) setDelay(active.delay);
  }, [active?.flightId, active?.delay]);

  /** On release, apply the new delay to the scenario on screen. */
  function commitDelay() {
    if (active && !busy && delay !== active.delay) onDelay(active.flightId, delay);
  }

  useEffect(() => {
    api
      .presets()
      .then(setPresets)
      .catch((e: unknown) => setPresetError(errorText(e, "Could not load suggestions.")));
  }, []);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearchError(null);
    setSearchPage(0);
    try {
      setResults(await api.flights(query.trim()));
    } catch (e: unknown) {
      setSearchError(errorText(e, "Search failed."));
    }
  }

  function start(flightId: string) {
    if (tab === "DELAY") onDelay(flightId, delay);
    else if (tab === "CANCEL") onCancel(flightId);
    else onAgent?.({ flight_id: flightId, delay_minutes: agentDelay, strategy: agentStrategy, note: agentNote.trim() });
  }

  return (
    <section className="launcher" aria-labelledby="launcher-title">
      <h2 id="launcher-title">New scenario</h2>

      {/* Search bar always at the top */}
      <form className="search launcher-search" onSubmit={search} role="search">
        <label htmlFor="flight-search" className="visually-hidden">
          Flight number, airport or aircraft
        </label>
        <input id="flight-search" placeholder="Search by flight number, airport or tail (e.g. G9519, SHJ, A6-ARI)"
          value={query} maxLength={10}
          onChange={(e) => setQuery(e.target.value.replace(/[^A-Za-z0-9-]/g, ""))} />
        <button type="submit">Search</button>
      </form>
      {searchError && <p className="error">{searchError}</p>}
      {results && results.length === 0 && <p className="muted small">No flights match.</p>}
      {results && results.length > 0 && (
        <>
          <ul className="preset-list">
            {results.slice(searchPage * searchPageSize, (searchPage + 1) * searchPageSize).map((f) => (
              <li key={f.flight_id}>
                <button type="button" className="preset" disabled={busy} onClick={() => start(f.flight_id)}>
                  <span className="preset-title">
                    <CarrierTail flightNumber={f.flight_number} />
                    {f.flight_number} {f.origin}→{f.destination}
                  </span>
                  <span className="small muted">
                    {utc(f.std)} · {f.tail} · {f.booked_seats}/{f.capacity} booked
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <Paginator total={results.length} page={searchPage} pageSize={searchPageSize}
            onPage={setSearchPage} onPageSize={setSearchPageSize} />
        </>
      )}

      {!hideTabNav && (
        <div className="tabs" role="tablist" aria-label="Disruption type" style={{ marginTop: "0.75rem" }}>
          <button type="button" role="tab" aria-selected={tab === "DELAY"} className={tab === "DELAY" ? "tab active" : "tab"}
            onClick={() => setTab("DELAY")}>
            A · Delay
          </button>
          <button type="button" role="tab" aria-selected={tab === "CANCEL"} className={tab === "CANCEL" ? "tab active" : "tab"}
            onClick={() => setTab("CANCEL")}>
            B · Cancellation
          </button>
          {onAgent && (
            <button type="button" role="tab" aria-selected={tab === "AGENT"} className={tab === "AGENT" ? "tab active" : "tab"}
              onClick={() => setTab("AGENT")}>
              Ask the agent
            </button>
          )}
        </div>
      )}

      {tab === "DELAY" && (
        <div className="field" style={{ marginTop: "0.5rem" }}>
          <label htmlFor="delay">
            Delay: <strong>{delay} min</strong>
          </label>
          <input id="delay" type="range" min={15} max={600} step={15} value={delay}
            onChange={(e) => setDelay(Number(e.target.value))}
            onPointerUp={commitDelay} onKeyUp={commitDelay} onTouchEnd={commitDelay} />
          <span className={active ? "small muted" : "small hint"}>
            {active
              ? delay === active.delay
                ? `Applied to ${active.flightNumber}. Move and release to re-run.`
                : `Release to re-run ${active.flightNumber} with ${delay} min…`
              : `Pick a flight below to analyse it with ${delay} min.`}
          </span>
        </div>
      )}

      {tab === "AGENT" && (
        <div className="agent-form" style={{ marginTop: "0.5rem" }}>
          <p className="small muted">
            The agent uses the recovery engine, explains each step and recommends one option. You review and approve it.
          </p>
          <div className="field">
            <label htmlFor="agent-delay">Delay</label>
            <select id="agent-delay" value={agentDelay ?? ""}
              onChange={(e) => setAgentDelay(e.target.value ? Number(e.target.value) : null)}>
              <option value="">Let the agent use the predicted delay</option>
              {AGENT_DELAYS.map((d) => (
                <option key={d} value={d}>
                  {d} min
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="agent-strategy">Strategy</label>
            <select id="agent-strategy" value={agentStrategy ?? ""}
              onChange={(e) => setAgentStrategy(e.target.value ? (e.target.value as StrategyKey) : null)}>
              <option value="">No preference</option>
              {STRATEGY_KEYS.map((k) => (
                <option key={k} value={k}>
                  {STRATEGY_LABEL[k]}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="agent-note">Note for the agent (optional)</label>
            <textarea id="agent-note" rows={2} maxLength={500} value={agentNote} placeholder="e.g. crew for A6-AOH times out at 18:00Z"
              onChange={(e) => setAgentNote(e.target.value)} />
          </div>
        </div>
      )}

      <h3>Suggested flights</h3>
      {presetError && <p className="error">{presetError}</p>}
      {!presets && !presetError && <p className="muted small">Finding suitable flights…</p>}
      {presets && tab !== "CANCEL" && (() => {
        const items = presets.delay;
        const page = presetPage;
        const ps = presetPageSize;
        return (
          <>
            <ul className="preset-list">
              {items.slice(page * ps, (page + 1) * ps).map((p) => (
                <li key={p.flight_id}>
                  <button type="button" className="preset" disabled={busy} onClick={() => start(p.flight_id)}>
                    <span className="preset-title">
                      <CarrierTail flightNumber={p.flight_number} />
                      {p.flight_number} {p.origin}→{p.destination}
                      {p.is_demo && <span className="chip chip-synthetic">Demo (synthetic)</span>}
                    </span>
                    <span className="small muted">
                      {utc(p.std)} · {p.tail} · turn {p.turn_minutes} min · {p.connecting_pax} connecting
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <Paginator total={items.length} page={page} pageSize={ps}
              onPage={setPresetPage} onPageSize={setPresetPageSize} />
          </>
        );
      })()}
      {presets && tab === "CANCEL" && (() => {
        const items = presets.cancel;
        const page = presetPage;
        const ps = presetPageSize;
        return (
          <>
            <ul className="preset-list">
              {items.slice(page * ps, (page + 1) * ps).map((p) => (
                <li key={p.flight_id}>
                  <button type="button" className="preset" disabled={busy} onClick={() => start(p.flight_id)}>
                    <span className="preset-title">
                      <CarrierTail flightNumber={p.flight_number} />
                      {p.flight_number} {p.origin}→{p.destination}
                    </span>
                    <span className="small muted">
                      {utc(p.std)} · {p.tail} · {p.booked_seats} booked · {p.free_seats} free seats on alternatives
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <Paginator total={items.length} page={page} pageSize={ps}
              onPage={setPresetPage} onPageSize={setPresetPageSize} />
          </>
        );
      })()}
    </section>
  );
}
