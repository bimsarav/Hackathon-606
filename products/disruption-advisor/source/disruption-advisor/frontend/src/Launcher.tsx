import { type FormEvent, useEffect, useState } from "react";
import { api, type CancelPreset, type DelayPreset, errorText, type FlightRow, type Meta } from "./api";
import { CarrierTail } from "./CarrierTail";
import { utc } from "./format";

interface Props {
  meta: Meta;
  busy: boolean;
  /** The delay scenario on screen, if any: moving the slider re-runs it. */
  active?: { flightId: string; flightNumber: string; delay: number } | null;
  onDelay: (flightId: string, delay: number) => void;
  onCancel: (flightId: string) => void;
}

type Tab = "DELAY" | "CANCEL";

/** Scenario launcher: suggested flights from the data (UC5 example scenario) or any flight by search. */
export function Launcher({ busy, active, onDelay, onCancel }: Props) {
  const [tab, setTab] = useState<Tab>("DELAY");
  const [presets, setPresets] = useState<{ delay: DelayPreset[]; cancel: CancelPreset[] } | null>(null);
  const [presetError, setPresetError] = useState<string | null>(null);
  const [delay, setDelay] = useState(150);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<FlightRow[] | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

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
    try {
      setResults(await api.flights(query.trim()));
    } catch (e: unknown) {
      setSearchError(errorText(e, "Search failed."));
    }
  }

  const start = (flightId: string) => (tab === "DELAY" ? onDelay(flightId, delay) : onCancel(flightId));

  return (
    <section className="launcher" aria-labelledby="launcher-title">
      <h2 id="launcher-title">New scenario</h2>
      <div className="tabs" role="tablist" aria-label="Disruption type">
        <button type="button" role="tab" aria-selected={tab === "DELAY"} className={tab === "DELAY" ? "tab active" : "tab"}
          onClick={() => setTab("DELAY")}>
          A · Delay
        </button>
        <button type="button" role="tab" aria-selected={tab === "CANCEL"} className={tab === "CANCEL" ? "tab active" : "tab"}
          onClick={() => setTab("CANCEL")}>
          B · Cancellation
        </button>
      </div>

      {tab === "DELAY" && (
        <div className="field">
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
              : `No delay scenario is open: pick a flight below to analyse it with ${delay} min.`}
          </span>
        </div>
      )}

      <h3>Suggested from the data</h3>
      {presetError && <p className="error">{presetError}</p>}
      {!presets && !presetError && <p className="muted">Finding suitable flights…</p>}
      {presets && tab === "DELAY" && (
        <ul className="preset-list">
          {presets.delay.map((p) => (
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
      )}
      {presets && tab === "CANCEL" && (
        <ul className="preset-list">
          {presets.cancel.map((p) => (
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
      )}

      <h3>Any flight</h3>
      <form className="search" onSubmit={search} role="search">
        <label htmlFor="flight-search" className="visually-hidden">
          Flight number, airport or aircraft
        </label>
        <input id="flight-search" placeholder="G9519, SHJ, A6-ARI" value={query} maxLength={10}
          onChange={(e) => setQuery(e.target.value.replace(/[^A-Za-z0-9-]/g, ""))} />
        <button type="submit">Search</button>
      </form>
      {searchError && <p className="error">{searchError}</p>}
      {results && results.length === 0 && <p className="muted">No flights match.</p>}
      {results && results.length > 0 && (
        <ul className="preset-list">
          {results.map((f) => (
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
      )}
    </section>
  );
}
