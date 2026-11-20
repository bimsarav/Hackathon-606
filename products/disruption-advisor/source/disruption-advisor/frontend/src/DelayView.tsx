import { useState } from "react";
import type { DelayResult, Meta, RecoveryOption, Scenario } from "./api";
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
  const [selected, setSelected] = useState<string>(result.recommended_key);
  const [allLegs, setAllLegs] = useState(false);
  const best = result.options.find((o) => o.key === result.recommended_key) ?? result.options[0];
  if (!best) return <p className="error">No recovery option could be computed for this flight.</p>;
  const shown = result.options.find((o) => o.key === selected) ?? best;
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

      <section className="kpis" aria-label="Recommended option at a glance">
        <Kpi label="Recommended" value={best.label} />
        <Kpi label="Total delay" value={minutes(best.total_delay_minutes)} sub={`${best.legs_delayed} leg(s) delayed`} />
        <Kpi label="Missed connections" value={num(best.misconnects)} sub={`of ${num(best.connections_checked)} checked`} />
        <Kpi label="Estimated cost" value={aed(best.cost_aed)}
          sub={worst.key !== best.key ? `saves ${aed(worst.cost_aed - best.cost_aed)} vs worst option` : "only feasible option"} />
      </section>

      <Explanation text={result.explanation.text} source={result.explanation.source} />

      <section aria-labelledby="options-title">
        <h2 id="options-title">Recovery options compared</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Option</th>
                <th scope="col" className="num">Delay</th>
                <th scope="col" className="num">Legs</th>
                <th scope="col" className="num">Pax delayed</th>
                <th scope="col" className="num">Missed conn.</th>
                <th scope="col" className="num">EU261</th>
                <th scope="col" className="num">Cost</th>
                <th scope="col">
                  <span className="visually-hidden">Show</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {result.options.map((o: RecoveryOption) => (
                <tr key={o.key} className={o.key === result.recommended_key ? "recommended" : ""}>
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
                  <td>
                    <button type="button" className="link" aria-pressed={selected === o.key} onClick={() => setSelected(o.key)}>
                      {selected === o.key ? "Shown below" : "Show legs"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <DecisionBar scenario={scenario} target={`option:${best.key}`} label="recommended option" />
      </section>

      <section aria-labelledby="legs-title">
        <h2 id="legs-title">Rotation impact: {shown.label}</h2>
        <p className="small muted">Every leg the option touches over the next {meta.horizon_days} days, new times in UTC.</p>
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
            {allLegs ? "Show only delayed legs" : `Show all ${shown.legs.length} legs (${shown.legs.length - keyLegs.length} more on time)`}
          </button>
        )}
      </section>

      <section aria-labelledby="pax-title">
        <h2 id="pax-title">Passengers still missing a connection ({num(result.misconnections.length)})</h2>
        {result.rebooking && (
          <p className="muted">
            {num(result.rebooking.protected)} rebooked on later flights within 24 h ·{" "}
            <strong>{num(result.rebooking.unprotected)}</strong> without a seat (next day + hotel, or refund).
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
