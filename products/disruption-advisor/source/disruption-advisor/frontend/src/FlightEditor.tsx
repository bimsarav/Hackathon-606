import { useCallback, useEffect, useState } from "react";
import { api, type EditableFlight, type EditablePassenger, errorText, type FlightEditSummary, type FlightRow } from "./api";
import { utc } from "./format";

const TIERS = ["none", "Basic", "Silver", "Gold", "Platinum"] as const;
const FREQS = ["occasional", "regular", "frequent", "unknown"] as const;
const TYPES = ["AD", "CH", "IN"] as const;
const FAMILIES = ["Basic", "Value", "Ultimate", "Other", "Staff/ID", "Bus"];

/** Evaluator: open an existing flight, edit its schedule, aircraft, seats and passengers in a table, save. The
 *  analysis then uses the edited data; Reset brings the real flight back. The real data files are never changed. */
export function FlightEditor() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<FlightRow[]>([]);
  const [searched, setSearched] = useState<string | null>(null); // the text the last search ran for
  const [data, setData] = useState<EditableFlight | null>(null);
  const [flight, setFlight] = useState({ std: "", sta: "", tail: "", capacity: 0, booked_seats: 0 });
  const [pax, setPax] = useState<EditablePassenger[]>([]);
  const [edits, setEdits] = useState<FlightEditSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshEdits = useCallback(() => { api.flightEdits().then(setEdits).catch(() => setEdits([])); }, []);
  useEffect(refreshEdits, [refreshEdits]);

  async function search(text: string) {
    const q = text.trim();
    if (q.length < 2) { setResults([]); setSearched(null); return; }
    try {
      setResults(await api.flights(q));
    } catch {
      setResults([]);
    }
    setSearched(q);
  }

  // Search as you type (after a short pause); the Search button and Enter search at once.
  useEffect(() => {
    const t = window.setTimeout(() => void search(query), 300);
    return () => window.clearTimeout(t);
  }, [query]);

  async function open(id: string) {
    setError(null); setMessage(null);
    try {
      const d = await api.editableFlight(id);
      setData(d);
      setFlight({ std: d.flight.std_hhmm, sta: d.flight.sta_hhmm, tail: d.flight.tail, capacity: d.flight.capacity, booked_seats: d.flight.booked_seats });
      setPax(d.passengers.map((p) => ({ ...p, fare_family: p.fare_family ?? "Basic", fare: Math.round((p.fare ?? 0) * 100) / 100, ssr: p.ssr ?? "", remove: false })));
      setResults([]); setQuery(""); setSearched(null);
    } catch (e) { setError(errorText(e, "Could not open the flight.")); }
  }

  const setP = (i: number, change: Partial<EditablePassenger>) => setPax((list) => list.map((p, j) => (j === i ? { ...p, ...change } : p)));

  async function save() {
    if (!data) return;
    setBusy(true); setError(null); setMessage(null);
    try {
      await api.saveFlightEdit(data.flight.flight_id, {
        flight: flight,
        passengers: pax.map((p) => ({ ...p, ssr: p.ssr ? p.ssr.toUpperCase() : null, fare: Number(p.fare) || 0 })),
      });
      setMessage(`Saved. ${data.flight.flight_number} on ${utc(data.flight.std)} now uses your edits: analyse it in Flight Delay or Cancellation to see the new results.`);
      await open(data.flight.flight_id);
      setMessage(`Saved. ${data.flight.flight_number} now uses your edits: analyse it in Flight Delay or Cancellation to see the new results.`);
      refreshEdits();
    } catch (e) { setError(errorText(e, "Could not save the changes.")); } finally { setBusy(false); }
  }

  async function reset(id: string) {
    setBusy(true); setError(null);
    try {
      await api.resetFlightEdit(id);
      setMessage(`${id.split("_")[0]} is back to the real data.`);
      refreshEdits();
      if (data?.flight.flight_id === id) await open(id);
    } catch (e) { setError(errorText(e, "Could not reset the flight.")); } finally { setBusy(false); }
  }

  const kept = pax.filter((p) => !p.remove).length;
  // Seats sold follows the passenger list (infants sit on a lap and take no seat); it can still be typed by hand.
  const seats = (p: EditablePassenger) => (p.pax_type === "IN" ? 0 : 1);
  function bumpSold(by: number) {
    if (by) setFlight((f) => ({ ...f, booked_seats: Math.max(0, f.booked_seats + by) }));
  }

  return (
    <section className="flight-editor" aria-labelledby="edit-title">
      <h3 id="edit-title">Edit an existing flight</h3>
      <p className="small muted">
        Change a real flight and its passengers, save, then analyse it again: every result (delay impact, rebooking,
        crew check, rewards) uses your edits. The real data and the trained models stay unchanged; Reset restores the flight.
      </p>
      <form className="flight-editor-search" onSubmit={(e) => { e.preventDefault(); void search(query); }}>
        <label htmlFor="edit-flight">Flight number</label>
        <div className="flight-editor-searchrow">
          <input id="edit-flight" placeholder="e.g. G9519" value={query} maxLength={8}
            onChange={(e) => setQuery(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))} />
          <button type="submit" className="primary">Search</button>
        </div>
      </form>
      {results.length > 0 && <p className="small">Pick the date to open the flight:</p>}
      {searched && results.length === 0 && <p className="small muted">No flights found for “{searched}”.</p>}
      {results.length > 0 && (
        <ul className="preset-list preset-chips" aria-label="Flights to edit">
          {results.slice(0, 12).map((f) => (
            <li key={f.flight_id}>
              <button type="button" className="preset preset-chip" onClick={() => void open(f.flight_id)}>
                <strong>{f.flight_number}</strong> {f.origin}→{f.destination}<span className="muted"> · {utc(f.std)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {edits.length > 0 && (
        <p className="small">
          Edited now:{" "}
          {edits.map((e) => (
            <span key={e.flight_id} className="edited-chip">
              <button type="button" className="link" onClick={() => void open(e.flight_id)}>{e.flight_number} {e.flight_id.slice(-12, -4)}</button>
              <button type="button" className="link small" disabled={busy} onClick={() => void reset(e.flight_id)}>Reset</button>
            </span>
          ))}
        </p>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      {message && <p className="small note" role="status">{message}</p>}

      {data && (
        <div className="flight-editor-form">
          <h4>
            {data.flight.flight_number} {data.flight.origin}→{data.flight.destination} · {utc(data.flight.std)}
            {data.edited && <span className="chip chip-warn">edited</span>}
          </h4>
          <div className="filter-row">
            <div className="filter-field"><label htmlFor="ed-std">Departure (UTC)</label>
              <input id="ed-std" type="time" value={flight.std} onChange={(e) => setFlight({ ...flight, std: e.target.value })} /></div>
            <div className="filter-field"><label htmlFor="ed-sta">Arrival (UTC)</label>
              <input id="ed-sta" type="time" value={flight.sta} onChange={(e) => setFlight({ ...flight, sta: e.target.value })} /></div>
            <div className="filter-field"><label htmlFor="ed-tail">Aircraft (tail)</label>
              <input id="ed-tail" value={flight.tail} maxLength={10} onChange={(e) => setFlight({ ...flight, tail: e.target.value.toUpperCase() })} /></div>
            <div className="filter-field"><label htmlFor="ed-cap">Seat capacity</label>
              <input id="ed-cap" type="number" min={1} max={600} value={flight.capacity} onChange={(e) => setFlight({ ...flight, capacity: Number(e.target.value) })} /></div>
            <div className="filter-field"><label htmlFor="ed-sold">Seats sold</label>
              <input id="ed-sold" type="number" min={0} max={600} value={flight.booked_seats} onChange={(e) => setFlight({ ...flight, booked_seats: Number(e.target.value) })} /></div>
          </div>
          <p className="small muted">{kept} passengers kept of {pax.length} listed{pax.some((p) => !p.customer_key) ? " (incl. added)" : ""}.
            Seats sold goes down by one for each passenger you remove and up for each you add (infants take no seat).</p>
          <div className="table-wrap flight-editor-table">
            <table aria-label="Passengers of the flight">
              <thead>
                <tr><th>PNR</th><th>Passenger</th><th>Type</th><th>Fare family</th><th className="num">Fare (AED)</th><th>Loyalty</th><th>Frequency</th><th>Special service</th><th>Remove</th></tr>
              </thead>
              <tbody>
                {pax.map((p, i) => (
                  <tr key={p.customer_key ?? `new-${i}`} className={p.remove ? "removed" : ""}>
                    <td>{p.customer_key ? p.pnr : (
                      <input aria-label={`PNR of new passenger ${i + 1}`} value={p.pnr} maxLength={12}
                        onChange={(e) => setP(i, { pnr: e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "") })} />)}</td>
                    <td className="small muted">{p.passenger_id ?? "new"}</td>
                    <td><select aria-label="Type" value={p.pax_type} onChange={(e) => {
                      const next = { ...p, pax_type: e.target.value as EditablePassenger["pax_type"] };
                      if (!p.remove) bumpSold(seats(next) - seats(p));
                      setP(i, { pax_type: next.pax_type }); }}>
                      {TYPES.map((t) => <option key={t}>{t}</option>)}</select></td>
                    <td><select aria-label="Fare family" value={p.fare_family ?? "Basic"} onChange={(e) => setP(i, { fare_family: e.target.value })}>
                      {[...new Set([...(p.fare_family ? [p.fare_family] : []), ...FAMILIES])].map((f) => <option key={f}>{f}</option>)}</select></td>
                    <td className="num"><input aria-label="Fare" type="number" min={0} value={p.fare ?? 0} onChange={(e) => setP(i, { fare: Number(e.target.value) })} /></td>
                    <td><select aria-label="Loyalty tier" value={p.loyalty_tier} onChange={(e) => setP(i, { loyalty_tier: e.target.value as EditablePassenger["loyalty_tier"] })}>
                      {TIERS.map((t) => <option key={t}>{t}</option>)}</select></td>
                    <td><select aria-label="Travel frequency" value={p.frequency} onChange={(e) => setP(i, { frequency: e.target.value as EditablePassenger["frequency"] })}>
                      {FREQS.map((t) => <option key={t}>{t}</option>)}</select></td>
                    <td><input aria-label="Special service" value={p.ssr ?? ""} maxLength={4} placeholder="e.g. WCHR"
                      onChange={(e) => setP(i, { ssr: e.target.value.toUpperCase().replace(/[^A-Z]/g, "") })} /></td>
                    <td><input type="checkbox" aria-label={`Remove ${p.pnr}`} checked={!!p.remove} onChange={(e) => { bumpSold((e.target.checked ? -1 : 1) * seats(p)); setP(i, { remove: e.target.checked }); }} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="testdata-actions">
            <button type="button" className="btn-outline" onClick={() => { bumpSold(1); setPax((list) => [...list, { customer_key: null, pnr: "NEW01", pax_type: "AD",
              fare_family: "Basic", fare: 300, ssr: "", loyalty_tier: "none", frequency: "occasional", remove: false }]); }}>Add passenger</button>
            <button type="button" className="primary" disabled={busy} onClick={() => void save()}>Save changes</button>
            <button type="button" className="link" disabled={busy} onClick={() => void open(data.flight.flight_id)}>Discard unsaved changes</button>
            {data.edited && <button type="button" className="reject" disabled={busy} onClick={() => void reset(data.flight.flight_id)}>Reset to real data</button>}
          </div>
        </div>
      )}
    </section>
  );
}
