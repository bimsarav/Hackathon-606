import type { CancelResult, Meta, Scenario } from "./api";
import { Kpi } from "./DelayView";
import { aed, num, utc } from "./format";
import { Assumptions, DecisionBar, Explanation, PassengerTable, WeightsPanel } from "./Shared";

interface Props {
  scenario: Scenario;
  result: CancelResult;
  meta: Meta;
  onUpdate: (s: Scenario) => void;
}

/** Scenario B: cancellation with too few seats; passengers ranked by tier and weights, rebooked within inventory. */
export function CancelView({ scenario, result, meta, onUpdate }: Props) {
  const f = result.flight;
  const reb = result.rebooking;
  const seats = reb ? reb.alternatives.reduce((s, a) => s + a.available_seats, 0) : 0;
  const tiers = result.tier_counts ?? {};

  return (
    <article className="result">
      <header className="result-head">
        <p className="eyebrow">Scenario B · Cancellation</p>
        <h1>
          {f.flight_number} {f.origin}→{f.destination} cancelled
        </h1>
        <p className="muted">
          Scheduled {utc(f.std)} · aircraft {f.tail} · {num(result.passengers.length)} passengers to re-accommodate (lap
          infants travel with their adult)
        </p>
      </header>

      <section className="kpis" aria-label="Re-accommodation at a glance">
        <Kpi label="Free seats on alternatives" value={num(seats)} sub={`${reb?.alternatives.length ?? 0} flights within 24 h`} />
        <Kpi label="Protected" value={num(reb?.protected ?? 0)} sub={`${reb?.groups_split ?? 0} booking(s) split`} />
        <Kpi label="Hotel rooms" value={num(reb?.hotel_rooms ?? 0)} sub={`care ${aed(reb?.care_cost_aed ?? 0)}`} />
        <Kpi label="Without a seat" value={num(reb?.unprotected ?? 0)} sub="next day + hotel, or refund" />
        <Kpi label="Estimated cost" value={aed(result.cost_total_aed)}
          sub={result.eu261_per_passenger_eur ? `incl. EU261 €${result.eu261_per_passenger_eur}/pax` : "no EU261 exposure"} />
      </section>

      <p className="tier-summary">
        <span className="tier tier-1">Care {tiers["1"] ?? 0}</span> <span className="tier tier-2">Urgent {tiers["2"] ?? 0}</span>{" "}
        <span className="tier tier-3">Standard {tiers["3"] ?? 0}</span>{" "}
        <span className="tier tier-nr">Non-rev {tiers["non_revenue"] ?? 0}</span>
        <span className="small muted"> · solver: {result.solver_status.toLowerCase()}</span>
      </p>

      <Explanation text={result.explanation.text} source={result.explanation.source} />

      {reb && reb.alternatives.length > 0 && (
        <section aria-labelledby="alts-title">
          <h2 id="alts-title">Alternative flights used</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Flight</th>
                  <th scope="col">Departs</th>
                  <th scope="col" className="num">Free seats</th>
                  <th scope="col" className="num">Assigned</th>
                  <th scope="col">Capacity source</th>
                </tr>
              </thead>
              <tbody>
                {reb.alternatives.map((a) => (
                  <tr key={a.flight_id}>
                    <td>{a.flight_number}</td>
                    <td>{utc(a.std)}</td>
                    <td className="num">{a.available_seats}</td>
                    <td className="num">{a.assigned}</td>
                    <td className="small">{a.capacity_source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {result.aircraft_follow_on && (
        <p className="note">
          The aircraft {f.tail} was due to fly {result.aircraft_follow_on.flight_number} {result.aircraft_follow_on.origin}→
          {result.aircraft_follow_on.destination} at {utc(result.aircraft_follow_on.std)}. Without this flight it is not in
          position: OCC must cover or cancel that leg (aircraft recovery is scenario A's tool).
        </p>
      )}

      <WeightsPanel meta={meta} scenario={scenario} onUpdate={onUpdate} />

      <section aria-labelledby="ranked-title">
        <h2 id="ranked-title">Passengers in priority order</h2>
        <PassengerTable scenario={scenario} rows={result.passengers} meta={meta} />
        <DecisionBar scenario={scenario} target="rebooking" label="rebooking plan" />
      </section>

      <Assumptions items={result.assumptions} />
    </article>
  );
}
