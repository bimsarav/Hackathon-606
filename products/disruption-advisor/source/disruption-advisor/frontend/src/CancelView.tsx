import { useState } from "react";
import type { CancelResult, Meta, Scenario } from "./api";
import { Fold, Kpi, PeopleBox, Tile } from "./DelayView";
import { aed, num, utc } from "./format";
import { RewardPanel } from "./RewardPanel";
import { Assumptions, DecisionBar, Explanation, PassengerTable, useAiExplanation, WeightsPanel, whyLabel } from "./Shared";

interface Props {
  scenario: Scenario;
  result: CancelResult;
  meta: Meta;
  onUpdate: (s: Scenario) => void;
}

type CancelSection = "why" | "weights" | "assumptions";
type CancelBox = "pax" | "alts" | "rewards";

function firstSentence(text: string): string {
  const one = text.split(/(?<=[.!?])\s/)[0] ?? text;
  return one.length > 90 ? `${one.slice(0, 89)}…` : one;
}

/** Scenario B: cancellation with too few seats; passengers ranked by tier and weights, rebooked within inventory.
 *  Same compact layout as the Flight Delay page: decision first, "at a glance" tiles, folding sections, three boxes. */
export function CancelView({ scenario, result, meta, onUpdate }: Props) {
  useAiExplanation(scenario, onUpdate);
  const f = result.flight;
  const reb = result.rebooking;
  // hub itineraries reuse flights, so only direct alternatives are summed (no double counting)
  const direct = reb ? reb.alternatives.filter((a) => !a.via) : [];
  const viaHub = reb ? reb.alternatives.length - direct.length : 0;
  const seats = direct.reduce((s, a) => s + a.available_seats, 0);
  const tiers = result.tier_counts ?? {};
  const [openSecs, setOpenSecs] = useState<Set<CancelSection>>(() => new Set<CancelSection>(["why"]));
  const [box, setBox] = useState<CancelBox | null>(null);
  const toggle = (id: CancelSection) => setOpenSecs((s) => {
    const next = new Set(s);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });
  const scrollTo = (id: string) => window.setTimeout(() => {
    const el = document.getElementById(id);
    const details = el?.querySelector("details");
    if (details) details.open = true;
    el?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }, 0);
  const reveal = (id: CancelSection) => { setOpenSecs((s) => new Set(s).add(id)); scrollTo(`sec-${id}`); };
  const showBox = (b: CancelBox) => { setBox(b); scrollTo("sec-people"); };
  const openBox = (b: CancelBox) => setBox((cur) => (cur === b ? null : b));

  return (
    <article className="result">
      <header className="result-head">
        <p className="eyebrow">Flight Cancellation</p>
        <h1>
          {f.flight_number} {f.origin}→{f.destination} cancelled
        </h1>
        <p className="muted">
          Scheduled {utc(f.std)} · aircraft {f.tail} · {num(result.passengers.length)} passengers to re-accommodate (lap
          infants travel with their adult)
        </p>
      </header>

      <section className="kpis" aria-label="Re-accommodation at a glance">
        <Kpi label="Free seats on alternatives" value={num(seats)}
          sub={`${direct.length} direct flights within 24 h${viaHub ? ` · ${viaHub} via SHJ` : ""}`} />
        <Kpi label="Protected" value={num(reb?.protected ?? 0)} sub={`${reb?.groups_split ?? 0} booking(s) split`} />
        <Kpi label="Hotel rooms" value={num(reb?.hotel_rooms ?? 0)} sub={`care ${aed(reb?.care_cost_aed ?? 0)}`} />
        <Kpi label="Without a seat" value={num(reb?.unprotected ?? 0)} sub="next day + hotel, or refund" />
        <Kpi label="Estimated cost" value={aed(result.cost_total_aed)}
          sub={result.eu261_per_passenger_eur ? `incl. EU261 €${result.eu261_per_passenger_eur}/pax` : "no EU261 exposure"} />
      </section>

      {/* The decision comes first: approve or reject the rebooking plan (recorded with who and when). */}
      <section className="decision-top" aria-label="Decision">
        <p className="small decision-top-label">
          <strong>Decision on the rebooking plan</strong>
          <span className="muted"> · {num(reb?.protected ?? 0)} protected, {num(reb?.unprotected ?? 0)} without a seat; review the passengers below</span>
        </p>
        <DecisionBar scenario={scenario} target="rebooking" label="rebooking plan" />
      </section>

      <nav className="glance" aria-label="On this page">
        <Tile label="Priority tiers" value={`${tiers["1"] ?? 0} care`}
          sub={`${tiers["2"] ?? 0} urgent · ${tiers["3"] ?? 0} standard · ${tiers["non_revenue"] ?? 0} non-rev`} onClick={() => showBox("pax")} />
        <Tile label="Why?" value={whyLabel(result.explanation.source, result.explanation.pending)} sub={firstSentence(result.explanation.text)} onClick={() => reveal("why")} />
        <Tile label="Passengers to rebook" value={num(result.passengers.length)}
          sub={reb ? `${num(reb.protected)} protected · ${num(reb.unprotected)} without a seat` : "priority order"}
          tone={reb && reb.unprotected > 0 ? "warn" : undefined} onClick={() => showBox("pax")} />
        <Tile label="Alternative flights" value={num(reb?.alternatives.length ?? 0)} sub={`${num(seats)} free seats within 24 h`} onClick={() => showBox("alts")} />
        <Tile label="Rewards & compensation" value={result.eu261_per_passenger_eur ? `€${result.eu261_per_passenger_eur}/pax` : "no EU261"}
          sub={`care ${aed(reb?.care_cost_aed ?? 0)}`} onClick={() => showBox("rewards")} />
        <Tile label="Priority weights" value="what-if" sub="re-rank inside each tier" onClick={() => reveal("weights")} />
        <Tile label="Assumptions" value={num(result.assumptions.length)} sub="data notes" onClick={() => reveal("assumptions")} />
      </nav>

      {result.aircraft_follow_on && (
        <p className="note">
          The aircraft {f.tail} was due to fly {result.aircraft_follow_on.flight_number} {result.aircraft_follow_on.origin}→
          {result.aircraft_follow_on.destination} at {utc(result.aircraft_follow_on.std)}. Without this flight it is not in
          position: OCC must cover or cancel that leg (aircraft recovery is scenario A's tool).
        </p>
      )}

      <Fold id="why" title="Why?" summary={firstSentence(result.explanation.text)} open={openSecs.has("why")} onToggle={() => toggle("why")}>
        <Explanation text={result.explanation.text} source={result.explanation.source} pending={result.explanation.pending} />
      </Fold>

      <Fold id="weights" title="Priority weights (what-if)" summary="change the weights to re-rank passengers inside each tier"
        open={openSecs.has("weights")} onToggle={() => toggle("weights")}>
        <WeightsPanel meta={meta} scenario={scenario} onUpdate={onUpdate} />
      </Fold>

      {/* Passengers: three boxes; a click opens that box's full detail below them. */}
      <section id="sec-people" aria-labelledby="people-title" className="people">
        <h2 id="people-title">Passengers</h2>
        <div className="model-grid">
          <PeopleBox kind="Rebooking plan" title="Passengers to rebook" active={box === "pax"} onOpen={() => openBox("pax")}
            stats={[
              { label: "protected", value: num(reb?.protected ?? 0) },
              { label: "without a seat", value: num(reb?.unprotected ?? 0) },
              { label: "bookings split", value: num(reb?.groups_split ?? 0) },
            ]} />
          <PeopleBox kind="Seats" title="Alternative flights" active={box === "alts"} onOpen={() => openBox("alts")}
            stats={[
              { label: "flights", value: num(reb?.alternatives.length ?? 0) },
              { label: "free seats", value: num(seats) },
              ...(viaHub ? [{ label: "via SHJ", value: num(viaHub) }] : []),
            ]} />
          <PeopleBox kind="Goodwill & EU261" title="Rewards & compensation" active={box === "rewards"} onOpen={() => openBox("rewards")}
            stats={[
              { label: "EU261 per passenger", value: result.eu261_per_passenger_eur ? `€${result.eu261_per_passenger_eur}` : "€0" },
              { label: "care cost", value: aed(reb?.care_cost_aed ?? 0) },
            ]} />
        </div>
        {box === "pax" && (
          <section aria-labelledby="ranked-title">
            <h2 id="ranked-title">Passengers in priority order</h2>
            <PassengerTable scenario={scenario} rows={result.passengers} meta={meta} />
          </section>
        )}
        {box === "alts" && reb && (
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
                      <td>
                        {a.flight_number}
                        {a.via && (
                          <span className="chip small" title={`Two flights through ${a.via}, sold as a connection; for passengers going to ${a.for_destination ?? "the same destination"}`}>
                            via {a.via}{a.for_destination ? ` → ${a.for_destination}` : ""}
                          </span>
                        )}
                      </td>
                      <td>{utc(a.std)}</td>
                      <td className="num">{a.available_seats}</td>
                      <td className="num">{a.assigned}</td>
                      <td className="small">{a.capacity_source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="small muted">Solver: {result.solver_status.toLowerCase()}.</p>
          </section>
        )}
        {box === "rewards" && <RewardPanel scenario={scenario} />}
      </section>

      <div id="sec-assumptions"><Assumptions items={result.assumptions} /></div>
    </article>
  );
}
