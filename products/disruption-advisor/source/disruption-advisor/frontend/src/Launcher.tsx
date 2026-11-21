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
import { DelaySlider, RowPredict } from "./PredictPanel";
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

export function Launcher({ meta, busy, active, onDelay, onCancel, onAgent, defaultTab, hideTabNav }: Props) {
  const [tab, setTab] = useState<Tab>(defaultTab ?? "DELAY");
  const [presets, setPresets] = useState<{ delay: DelayPreset[]; cancel: CancelPreset[] } | null>(null);
  const [presetError, setPresetError] = useState<string | null>(null);
  const [delay, setDelay] = useState(150);
  const [query, setQuery] = useState("");
  const [originFilter, setOriginFilter] = useState("");
  const [destFilter, setDestFilter] = useState("");
  const [tailFilter, setTailFilter] = useState("");
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
  const [advanced, setAdvanced] = useState(false);
  const [advInbound, setAdvInbound] = useState<number | null>(null);
  const [advDeparture, setAdvDeparture] = useState<number | null>(null);
  // Once a flight is chosen (or one is already on screen) the lists fold away to save space; one click brings them back.
  const [listHidden, setListHidden] = useState(Boolean(active));
  const [chosen, setChosen] = useState<string | null>(active?.flightNumber ?? null);
  const [moreFilters, setMoreFilters] = useState(false);
  // The day before "now" too: the operating data starts a day early (and has the crew roster).
  const days = Array.from({ length: (meta?.horizon_days ?? 7) + 2 }, (_, i) => {
    const d = new Date(`${(meta?.now_utc ?? "2026-11-20T00:00:00").slice(0, 10)}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() + i - 1);
    return d.toISOString().slice(0, 10);
  });
  const day = fromDate && fromDate === toDate ? fromDate : "";
  function pickDay(value: string) {
    setFromDate(value); setToDate(value); setSearchPage(0); setPresetPage(0);
  }

  function inRange(std: string, origin?: string, destination?: string, tail?: string, flightNumber?: string): boolean {
    const day = std.slice(0, 10);
    const q = query.trim().toUpperCase();
    if (q && flightNumber && !flightNumber.toUpperCase().includes(q)) return false; // main box: flight number only
    if (tailFilter && tail && !tail.toUpperCase().includes(tailFilter)) return false;
    if (fromDate && day < fromDate) return false;
    if (toDate && day > toDate) return false;
    if (originFilter && origin && !origin.includes(originFilter)) return false;
    if (destFilter && destination && !destination.includes(destFilter)) return false;
    return true;
  }

  function handleFromDate(v: string) { setFromDate(v); setSearchPage(0); setPresetPage(0); }
  function handleToDate(v: string)   { setToDate(v);   setSearchPage(0); setPresetPage(0); }

  function resetFilters() {
    setQuery(""); setOriginFilter(""); setDestFilter(""); setTailFilter("");
    setFromDate(""); setToDate("");
    setSearchPage(0); setPresetPage(0);
    setResults(null); setSearchError(null); setListHidden(false);
  }

  // Keep the slider in step with the scenario on screen (e.g. one reopened from history).
  useEffect(() => {
    if (active) setDelay(active.delay);
  }, [active?.flightId, active?.delay]);

  // Advanced search: the greyed-out Delay slider follows the two sliders (departure delay first, else the inbound
  // arrival delay) so the scenario is analysed with the same timing the predictions use.
  useEffect(() => {
    const known = advanced ? (advDeparture ?? advInbound) : null;
    if (known !== null) setDelay(Math.min(600, Math.max(15, Math.round(known / 15) * 15)));
  }, [advanced, advDeparture, advInbound]);

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

  async function runSearch(text: string) {
    setSearchError(null);
    setSearchPage(0);
    setListHidden(false);
    try {
      setResults(await api.flights(text));
    } catch (e: unknown) {
      setSearchError(errorText(e, "Search failed."));
    }
  }

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runSearch(query.trim() || tailFilter.trim()); // an empty search lists the next flights
  }

  // Search as you type (2+ characters, after a short pause); an empty box goes back to the suggestions.
  useEffect(() => {
    const text = query.trim() || tailFilter.trim();
    if (text.length === 0) { setResults(null); return; }
    if (text.length < 2) return;
    const timer = window.setTimeout(() => void runSearch(text), 350);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, tailFilter]);

  function start(flightId: string) {
    setListHidden(true);
    setChosen(flightId.split("_")[0] ?? flightId);
    if (tab === "DELAY") onDelay(flightId, delay);
    else if (tab === "CANCEL") onCancel(flightId);
    else onAgent?.({ flight_id: flightId, delay_minutes: agentDelay, strategy: agentStrategy, note: agentNote.trim() });
  }

  return (
    <section className="launcher" aria-label="New scenario">

      {/* Once a flight is chosen the search folds to one line (flight, delay slider, change); one click restores it. */}
      {listHidden && (
        <div className="filter-card filter-compact">
          <span className="filter-compact-flight">
            <span className="small muted">Flight</span> <strong>{active?.flightNumber ?? chosen ?? "chosen"}</strong>
          </span>
          {tab === "DELAY" && active && (
            <div className="filter-compact-delay">
              <label htmlFor="delay">Delay: <strong>{delay} min</strong></label>
              <input id="delay" type="range" min={15} max={600} step={15} value={delay} disabled={advanced}
                onChange={(e) => setDelay(Number(e.target.value))}
                onPointerUp={commitDelay} onKeyUp={commitDelay} onTouchEnd={commitDelay} />
              <span className="small muted">{delay === active.delay ? "release to re-run" : `release to re-run with ${delay} min`}</span>
            </div>
          )}
          <button type="button" className="link" onClick={() => setListHidden(false)}>Change flight or search</button>
        </div>
      )}

      {/* Multi-column filter card */}
      {!listHidden && (
      <div className="filter-card search-bar">
        <form onSubmit={search}>
          {/* One line: search box, (scenario type,) delay */}
          <div className="search-row">
            <div className="search-box">
              <label htmlFor="ff-flight" className="visually-hidden">Flight number</label>
              <span className="search-icon" aria-hidden="true">⌕</span>
              <input id="ff-flight" placeholder="Flight number (e.g. G9519)" autoComplete="off"
                value={query} maxLength={8}
                onChange={(e) => setQuery(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))} />
              <button type="submit" className="search-go">Search</button>
            </div>
            {!hideTabNav && (
              <div className="filter-field">
                <label htmlFor="ff-type">Scenario</label>
                <select id="ff-type" value={tab} onChange={(e) => setTab(e.target.value as Tab)}>
                  <option value="DELAY">Delay</option>
                  <option value="CANCEL">Cancellation</option>
                  {onAgent && <option value="AGENT">Predict the Flight Delay</option>}
                </select>
              </div>
            )}
            {tab === "DELAY" && (
              <div className="search-delay">
                <label htmlFor="delay">Delay: <strong>{delay} min</strong></label>
                <input id="delay" type="range" min={15} max={600} step={15} value={delay} disabled={advanced}
                  onChange={(e) => setDelay(Number(e.target.value))}
                  onPointerUp={commitDelay} onKeyUp={commitDelay} onTouchEnd={commitDelay} />
              </div>
            )}
          </div>
          {/* Day chips + more filters */}
          <div className="search-days" role="group" aria-label="Departure day (UTC)">
            <span className="small muted">Day</span>
            <button type="button" className={`chip-btn${day === "" && !fromDate && !toDate ? " on" : ""}`} aria-pressed={day === "" && !fromDate && !toDate}
              onClick={() => pickDay("")}>All</button>
            {days.map((d) => {
              const label = new Date(`${d}T00:00:00Z`).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", timeZone: "UTC" });
              return (
                <button key={d} type="button" className={`chip-btn${day === d ? " on" : ""}`} aria-pressed={day === d} onClick={() => pickDay(d)}>{label}</button>
              );
            })}
            <button type="button" className="link small search-more" aria-expanded={moreFilters} onClick={() => setMoreFilters((v) => !v)}>
              {moreFilters ? "Fewer filters ▴" : "More filters ▾"}
            </button>
          </div>
          {moreFilters && (
            <div className="search-filters">
              <div className="filter-row">
                <div className="filter-field">
                  <label htmlFor="ff-tail">Aircraft (tail)</label>
                  <input id="ff-tail" placeholder="e.g. A6-ARI" value={tailFilter} maxLength={10}
                    onChange={(e) => setTailFilter(e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, ""))} />
                </div>
                <div className="filter-field">
                  <label htmlFor="ff-origin">Origin</label>
                  <input id="ff-origin" placeholder="e.g. SHJ" value={originFilter} maxLength={4}
                    onChange={(e) => setOriginFilter(e.target.value.toUpperCase().replace(/[^A-Z]/g, ""))} />
                </div>
                <div className="filter-field">
                  <label htmlFor="ff-dest">Destination</label>
                  <input id="ff-dest" placeholder="e.g. DXB" value={destFilter} maxLength={4}
                    onChange={(e) => setDestFilter(e.target.value.toUpperCase().replace(/[^A-Z]/g, ""))} />
                </div>
                <div className="filter-field">
                  <label htmlFor="dep-from">Dep. Date From (UTC)</label>
                  <input id="dep-from" type="date" value={fromDate} onChange={(e) => handleFromDate(e.target.value)} />
                </div>
                <div className="filter-field">
                  <label htmlFor="dep-to">Dep. Date To (UTC)</label>
                  <input id="dep-to" type="date" value={toDate} onChange={(e) => handleToDate(e.target.value)} />
                </div>
                <div className="filter-actions">
                  <button type="button" className="btn-outline" onClick={resetFilters}>Reset</button>
                </div>
              </div>
              {/* Advanced search - what is known today; applies to every listed flight, replaces the Delay slider */}
              {tab !== "CANCEL" && (
                <div className="filter-row-advanced">
                  <label className="small">
                    <input type="checkbox" checked={advanced} onChange={(e) => setAdvanced(e.target.checked)} /> Advanced search
                    (add what is known today; the Delay slider is switched off). Predictions below always update on their own.
                  </label>
                  {advanced && (
                    <div className="filter-row-delay">
                      <div className="filter-field filter-field-delay">
                        <DelaySlider id="adv-inbound" label="Arrival: inbound aircraft arrived late by" value={advInbound}
                                     onChange={setAdvInbound} />
                      </div>
                      <div className="filter-field filter-field-delay">
                        <DelaySlider id="adv-departure" label="Departure: this flight departed / will depart late by"
                                     value={advDeparture} onChange={setAdvDeparture} />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          {tab === "DELAY" && !active && <p className="small muted search-hint">Pick a flight below to analyse it with {delay} min.</p>}
        </form>
      </div>
      )}

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

      {listHidden ? null : (
        <>
        {searchError && <p className="error">{searchError}</p>}
        {results && (
          <div className="list-head">
            <h3>{(query.trim() || tailFilter.trim())
              ? `${results.filter((f) => inRange(f.std, f.origin, f.destination, f.tail, f.flight_number)).length} flights match “${query.trim() || tailFilter.trim()}”`
              : `Next ${results.filter((f) => inRange(f.std, f.origin, f.destination, f.tail, f.flight_number)).length} flights`}</h3>
            <button type="button" className="link small" onClick={() => { setQuery(""); setTailFilter(""); setResults(null); }}>Clear search · back to suggestions</button>
          </div>
        )}
        {results && results.length > 0 && (() => {
          const filtered = results.filter((f) => inRange(f.std, f.origin, f.destination, f.tail, f.flight_number));
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
                        {tab !== "CANCEL" && <RowPredict flightId={f.flight_id} inbound={advanced ? advInbound : null} departure={advanced ? advDeparture : null} />}
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

        {!results && (
        <>
        <h3>Suggested flights</h3>
        {presetError && <p className="error">{presetError}</p>}
        {!presets && !presetError && <p className="muted small">Finding suitable flights…</p>}
        {presets && tab !== "CANCEL" && (() => {
          const items = presets.delay.filter((p) => inRange(p.std, p.origin, p.destination, p.tail, p.flight_number));
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
                        <RowPredict flightId={p.flight_id} inbound={advanced ? advInbound : null} departure={advanced ? advDeparture : null} />
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
          const items = presets.cancel.filter((p) => inRange(p.std, p.origin, p.destination, p.tail, p.flight_number));
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
        </>
        )}
        </>
      )}
    </section>
  );
}
