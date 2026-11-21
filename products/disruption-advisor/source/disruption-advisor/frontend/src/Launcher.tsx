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
  const [originFilter, setOriginFilter] = useState("");
  const [destFilter, setDestFilter] = useState("");
  const [results, setResults] = useState<FlightRow[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [agentDelay, setAgentDelay] = useState<number | null>(null);
  const [agentStrategy, setAgentStrategy] = useState<StrategyKey | null>(null);
  const [agentNote, setAgentNote] = useState("");
  const [searchPage, setSearchPage] = useState(0);
  const [searchPageSize, setSearchPageSize] = useState<number>(5);
  const [presetPage, setPresetPage] = useState(0);
  const [presetPageSize, setPresetPageSize] = useState<number>(5);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  function inRange(std: string, origin?: string, destination?: string): boolean {
    const day = std.slice(0, 10);
    if (fromDate && day < fromDate) return false;
    if (toDate && day > toDate) return false;
    if (originFilter && origin && !origin.includes(originFilter)) return false;
    if (destFilter && destination && !destination.includes(destFilter)) return false;
    return true;
  }

  function handleFromDate(v: string) { setFromDate(v); setSearchPage(0); setPresetPage(0); }
  function handleToDate(v: string)   { setToDate(v);   setSearchPage(0); setPresetPage(0); }

  function resetFilters() {
    setQuery(""); setOriginFilter(""); setDestFilter("");
    setFromDate(""); setToDate("");
    setSearchPage(0); setPresetPage(0);
    setResults(null); setSearchError(null);
  }

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

      {/* Multi-column filter card */}
      <div className="filter-card">
        <form onSubmit={search}>
          {/* Row 1: flight fields + type + dep from */}
          <div className="filter-row">
            <div className="filter-field">
              <label htmlFor="ff-flight">Flight / Tail</label>
              <input id="ff-flight" placeholder="e.g. G9519, A6-ARI"
                value={query} maxLength={10}
                onChange={(e) => setQuery(e.target.value.replace(/[^A-Za-z0-9-]/g, ""))} />
            </div>
            <div className="filter-field">
              <label htmlFor="ff-origin">Origin</label>
              <input id="ff-origin" placeholder="e.g. SHJ"
                value={originFilter} maxLength={4}
                onChange={(e) => setOriginFilter(e.target.value.toUpperCase().replace(/[^A-Z]/g, ""))} />
            </div>
            <div className="filter-field">
              <label htmlFor="ff-dest">Destination</label>
              <input id="ff-dest" placeholder="e.g. DXB"
                value={destFilter} maxLength={4}
                onChange={(e) => setDestFilter(e.target.value.toUpperCase().replace(/[^A-Z]/g, ""))} />
            </div>
            {!hideTabNav && (
              <div className="filter-field">
                <label htmlFor="ff-type">Scenario Type</label>
                <select id="ff-type" value={tab} onChange={(e) => setTab(e.target.value as Tab)}>
                  <option value="DELAY">Delay</option>
                  <option value="CANCEL">Cancellation</option>
                  {onAgent && <option value="AGENT">Ask the agent</option>}
                </select>
              </div>
            )}
            <div className="filter-field">
              <label htmlFor="dep-from">Dep. Date From (UTC)</label>
              <input id="dep-from" type="date" value={fromDate}
                onChange={(e) => handleFromDate(e.target.value)} />
            </div>
          </div>
          {/* Row 2: dep to + delay slider + actions */}
          <div className="filter-row-b">
            <div className="filter-field">
              <label htmlFor="dep-to">Dep. Date To (UTC)</label>
              <input id="dep-to" type="date" value={toDate}
                onChange={(e) => handleToDate(e.target.value)} />
            </div>
            {tab === "DELAY" && (
              <div className="filter-field filter-field-delay">
                <label htmlFor="delay">Delay: <strong>{delay} min</strong></label>
                <input id="delay" type="range" min={15} max={600} step={15} value={delay}
                  onChange={(e) => setDelay(Number(e.target.value))}
                  onPointerUp={commitDelay} onKeyUp={commitDelay} onTouchEnd={commitDelay} />
              </div>
            )}
            <div className="filter-actions">
              <button type="button" className="btn-outline" onClick={resetFilters}>Reset</button>
              <button type="submit">Search</button>
            </div>
          </div>
        </form>
        {tab === "DELAY" && (
          <p className={`small ${active ? "muted" : "hint"}`} style={{ marginTop: "0.5rem", marginBottom: 0 }}>
            {active
              ? delay === active.delay
                ? `Applied to ${active.flightNumber}. Move and release to re-run.`
                : `Release to re-run ${active.flightNumber} with ${delay} min…`
              : `Pick a flight below to analyse it with ${delay} min.`}
          </p>
        )}
      </div>

      {tab === "AGENT" && onAgent && (
        <div className="agent-form">
          <p className="small muted">
            The agent uses the recovery engine, explains each step and recommends one option. You review and approve it.
          </p>
          <div className="field">
            <label htmlFor="agent-delay">Delay</label>
            <select id="agent-delay" value={agentDelay ?? ""}
              onChange={(e) => setAgentDelay(e.target.value ? Number(e.target.value) : null)}>
              <option value="">Let the agent use the predicted delay</option>
              {AGENT_DELAYS.map((d) => (
                <option key={d} value={d}>{d} min</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="agent-strategy">Strategy</label>
            <select id="agent-strategy" value={agentStrategy ?? ""}
              onChange={(e) => setAgentStrategy(e.target.value ? (e.target.value as StrategyKey) : null)}>
              <option value="">No preference</option>
              {STRATEGY_KEYS.map((k) => (
                <option key={k} value={k}>{STRATEGY_LABEL[k]}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="agent-note">Note for the agent (optional)</label>
            <textarea id="agent-note" rows={2} maxLength={500} value={agentNote}
              placeholder="e.g. crew for A6-AOH times out at 18:00Z"
              onChange={(e) => setAgentNote(e.target.value)} />
          </div>
        </div>
      )}

      {searchError && <p className="error">{searchError}</p>}
      {results && results.length === 0 && <p className="muted small">No flights match.</p>}
      {results && results.length > 0 && (() => {
        const filtered = results.filter((f) => inRange(f.std, f.origin, f.destination));
        return (
          <>
            <ul className="preset-list">
              {filtered.slice(searchPage * searchPageSize, (searchPage + 1) * searchPageSize).map((f) => (
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
            <Paginator total={filtered.length} page={searchPage} pageSize={searchPageSize}
              onPage={setSearchPage} onPageSize={setSearchPageSize} />
            {filtered.length === 0 && <p className="muted small">No flights in that date range.</p>}
          </>
        );
      })()}

      <h3>Suggested flights</h3>
      {presetError && <p className="error">{presetError}</p>}
      {!presets && !presetError && <p className="muted small">Finding suitable flights…</p>}
      {presets && tab !== "CANCEL" && (() => {
        const items = presets.delay.filter((p) => inRange(p.std, p.origin, p.destination));
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
        const items = presets.cancel.filter((p) => inRange(p.std, p.origin, p.destination));
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
