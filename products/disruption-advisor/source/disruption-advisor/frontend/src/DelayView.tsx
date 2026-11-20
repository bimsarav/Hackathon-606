import { useState } from "react";
import { api, type DelayResult, errorText, type Meta, type RecoveryOption, type Scenario } from "./api";
import { aed, hhmm, minutes, num, utc } from "./format";
import { Assumptions, DecisionBar, Explanation, PassengerTable, WeightsPanel } from "./Shared";

interface Props {
  scenario: Scenario;
  result: DelayResult;
  meta: Meta;
  onUpdate: (s: Scenario) => void;
}

/** Scenario A: delay impact along the rotation, recovery options compared, misconnecting passengers rebooked. */
export function DelayView({ scenario, result, meta, onUpdate }: Props) {
  const [allLegs, setAllLegs] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [selectError, setSelectError] = useState<string | null>(null);
  const best = result.options.find((o) => o.key === result.recommended_key) ?? result.options[0];
  if (!best) return <p className="error">No recovery option could be computed for this flight.</p>;
  const selectedKey = result.selected_key ?? result.recommended_key;
  const shown = result.options.find((o) => o.key === selectedKey) ?? best;
  const override = shown.key !== best.key;

  /** Choosing an option re-runs the passenger plan, costs and explanation for that option on the server. */
  async function choose(key: string) {
    if (key === selectedKey || busy) return;
    setBusy(key);
    setSelectError(null);
    try {
      onUpdate(await api.selectOption(scenario.id, key));
    } catch (e: unknown) {
      setSelectError(errorText(e, "Could not switch to that option."));
    } finally {
      setBusy(null);
    }
  }
  const worst = result.options.reduce((a, b) => (b.cost_aed > a.cost_aed ? b : a), best);
  // Delayed legs always; legs that are only re-assigned (on time) are summarised unless expanded.
  const keyLegs = shown.legs.filter((l, i) => l.delay_minutes > 0 || i < 4);
  const legs = allLegs ? shown.legs : keyLegs;
  const f = result.flight;

  return (
    <article className="result">
      <header className="result-head">
        <p className="eyebrow">Scenario A · Delay</p>
        <h1>
          {f.flight_number} {f.origin}→{f.destination} +{minutes(result.delay_minutes)}
        </h1>
        <p className="muted">
          Scheduled {utc(f.std)} · aircraft {f.tail} ({f.aircraft_model}, {f.capacity} seats) · {num(f.booked_pax)} booked
        </p>
      </header>

      <section className="kpis" aria-label="Selected option at a glance">
        <Kpi label={override ? "Selected (override)" : "Recommended"} value={shown.label}
          sub={override ? `Recommended: ${best.label}` : undefined} />
        <Kpi label="Total delay" value={minutes(shown.total_delay_minutes)} sub={`${shown.legs_delayed} flight(s) delayed`} />
        <Kpi label="Missed connections" value={num(shown.misconnects)} sub={`of ${num(shown.connections_checked)} checked`} />
        <Kpi label="Estimated cost" value={aed(shown.cost_aed)}
          sub={override ? `${aed(shown.cost_aed - best.cost_aed)} more than recommended`
            : worst.key !== best.key ? `saves ${aed(worst.cost_aed - best.cost_aed)} vs worst option` : "only feasible option"} />
      </section>

      <Explanation text={result.explanation.text} source={result.explanation.source} />

      <section aria-labelledby="options-title">
        <h2 id="options-title">Recovery options compared</h2>
        <p className="small muted">Click an option to see its flights, passengers and cost. The recommendation is the cheapest.</p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Option</th>
                <th scope="col" className="num">Delay</th>
                <th scope="col" className="num">Flights delayed</th>
                <th scope="col" className="num">Pax delayed</th>
                <th scope="col" className="num">Missed conn.</th>
                <th scope="col" className="num">EU261</th>
                <th scope="col" className="num">Cost</th>
                <th scope="col">
                  <span className="visually-hidden">Selected</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {result.options.map((o: RecoveryOption) => (
                <tr key={o.key} tabIndex={0} aria-selected={o.key === selectedKey}
                  className={["option-row", o.key === result.recommended_key ? "recommended" : "",
                    o.key === selectedKey ? "selected" : ""].join(" ")}
                  onClick={() => choose(o.key)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); void choose(o.key); } }}>
                  <th scope="row">
                    {o.label}
                    {o.key === result.recommended_key && <span className="chip chip-ok">Recommended</span>}
                  </th>
                  <td className="num">{minutes(o.total_delay_minutes)}</td>
                  <td className="num">{o.legs_delayed}</td>
                  <td className="num">{num(o.delayed_passengers)}</td>
                  <td className="num">{num(o.misconnects)}</td>
                  <td className="num">€{num(o.eu261_compensation_eur)}</td>
                  <td className="num">{aed(o.cost_aed)}</td>
                  <td className="small">
                    {busy === o.key ? "Updating…" : o.key === selectedKey ? <strong>Selected</strong> : "Select"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {selectError && (
          <p className="error" role="alert">
            {selectError}
          </p>
        )}
        {override && (
          <p className="note">
            You selected an option that is not the recommendation. Approving it is recorded as an override and needs a
            reason in the comment.
          </p>
        )}
        <DecisionBar scenario={scenario} target={`option:${shown.key}`}
          label={override ? "selected option (override)" : "recommended option"} requireComment={override} />
      </section>

      <section aria-labelledby="legs-title">
        <h2 id="legs-title">Flights affected: {shown.label}</h2>
        <p className="small muted">Every flight this option touches over the next {meta.horizon_days} days, new times in UTC.</p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Flight</th>
                <th scope="col">Route</th>
                <th scope="col">Aircraft</th>
                <th scope="col">Scheduled</th>
                <th scope="col">New</th>
                <th scope="col" className="num">Delay</th>
                <th scope="col" className="num">Pax</th>
              </tr>
            </thead>
            <tbody>
              {legs.map((l) => (
                <tr key={l.flight_id} className={l.delay_minutes > 0 ? "late" : ""}>
                  <td>{l.flight_number}</td>
                  <td>
                    {l.origin}→{l.destination}
                  </td>
                  <td>
                    {l.operated_by}
                    {l.operated_by !== l.scheduled_tail && <span className="chip small">swapped from {l.scheduled_tail}</span>}
                  </td>
                  <td>{utc(l.std)}</td>
                  <td>
                    {hhmm(l.new_std)}–{hhmm(l.new_sta)}
                  </td>
                  <td className="num">{l.delay_minutes > 0 ? `+${minutes(l.delay_minutes)}` : "on time"}</td>
                  <td className="num">{num(l.booked_pax)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {shown.legs.length > keyLegs.length && (
          <button type="button" className="link" onClick={() => setAllLegs(!allLegs)}>
            {allLegs ? "Show only delayed flights" : `Show all ${shown.legs.length} flights (${shown.legs.length - keyLegs.length} more on time)`}
          </button>
        )}
      </section>

      <section aria-labelledby="pax-title">
        <h2 id="pax-title">Passengers still missing a connection ({num(result.misconnections.length)})</h2>
        {result.rebooking && (
          <p className="muted">
            {num(result.rebooking.protected)} rebooked on later flights within 24 h ·{" "}
            <strong>{num(result.rebooking.unprotected)}</strong> without a seat (next day + hotel, or refund)
            {result.rebooking.hotel_rooms ? ` · ${num(result.rebooking.hotel_rooms)} hotel rooms` : ""}
            {result.rebooking.care_cost_aed ? ` · care ${aed(result.rebooking.care_cost_aed)}` : ""}.
          </p>
        )}
        {result.passengers.length > 0 && <WeightsPanel meta={meta} scenario={scenario} onUpdate={onUpdate} />}
        <PassengerTable scenario={scenario} rows={result.passengers} meta={meta} />
        {result.passengers.length > 0 && <DecisionBar scenario={scenario} target="rebooking" label="rebooking plan" />}
      </section>

      <Assumptions items={result.assumptions} />
    </article>
  );
}

export function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="kpi">
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
      {sub && <span className="kpi-sub">{sub}</span>}
    </div>
  );
}
