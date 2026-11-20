import { Fragment, useEffect, useState } from "react";
import { api, type ConnectionRisk, errorText, type ModelCard, type RiskFlight, type Watchlist } from "./api";
import { Kpi } from "./DelayView";
import { minutes, num, utc } from "./format";

const pct = (p: number): string => `${Math.round(p * 100)}%`;
const BAND_LABEL = { high: "High", medium: "Medium", low: "Low" } as const;

interface Props {
  /** Opens Scenario A for the flight with the given delay (a person still reviews and approves). */
  onAnalyse: (flightId: string, delay: number) => void;
  busy: boolean;
}

/** Phase 2: flights likely to be late in the next 7 days, ranked by expected missed connections, with reasons. */
export function WatchlistView({ onAnalyse, busy }: Props) {
  const [band, setBand] = useState<"all" | "medium" | "high">("medium");
  const [sort, setSort] = useState<"misconnects" | "delay">("misconnects");
  const [data, setData] = useState<Watchlist | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    api
      .watchlist(band, sort)
      .then(setData)
      .catch((e: unknown) => setError(errorText(e, "Could not load the watchlist.")));
  }, [band, sort]);

  return (
    <article className="result">
      <header className="result-head">
        <p className="eyebrow">Phase 2 · Predict</p>
        <h1>Delay watchlist: next 7 days</h1>
        <p className="muted">
          Chance of a late departure for every flight, from the 2026 history and what is known a week ahead (schedule,
          aircraft plan, bookings, recent delays). Ranked by expected missed connections. A prediction is not a
          decision: open a flight to analyse it as a delay scenario.
        </p>
      </header>

      {data && (
        <section className="kpis" aria-label="Watchlist at a glance">
          <Kpi label="Flights listed" value={num(data.totals.flights)} />
          <Kpi label="High risk" value={num(data.totals.high)} sub="60+ min delay 30% likely or more" />
          <Kpi label="Medium risk" value={num(data.totals.medium)} sub="60+ min delay 15–30% likely" />
          <Kpi label="Expected missed connections" value={num(Math.round(data.totals.expected_misconnects ?? 0))}
            sub="sum of passenger risks" />
        </section>
      )}

      <div className="watch-filters" role="group" aria-label="Filter the watchlist">
        <label>
          Risk{" "}
          <select value={band} onChange={(e) => setBand(e.target.value as typeof band)}>
            <option value="high">High only</option>
            <option value="medium">Medium and high</option>
            <option value="all">All flights</option>
          </select>
        </label>
        <label>
          Sort by{" "}
          <select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}>
            <option value="misconnects">Expected missed connections</option>
            <option value="delay">Chance of a 60+ min delay</option>
          </select>
        </label>
      </div>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {data && data.flights.length === 0 && <p className="muted">No flights match this filter.</p>}
      {data && data.flights.length > 0 && (
        <div className="table-wrap">
          <table aria-label="Flights at risk">
            <thead>
              <tr>
                <th scope="col">Flight</th>
                <th scope="col">Departs</th>
                <th scope="col">Risk</th>
                <th scope="col" className="num">15+ min</th>
                <th scope="col" className="num">60+ min</th>
                <th scope="col" className="num" title="Delay exceeded with a 20% chance">Plan for</th>
                <th scope="col" className="num">Connecting</th>
                <th scope="col" className="num">Expected missed</th>
                <th scope="col">Main reason</th>
              </tr>
            </thead>
            <tbody>
              {data.flights.map((f) => (
                <Fragment key={f.flight_id}>
                  <tr
                    className={`clickable ${open === f.flight_id ? "selected" : ""}`}
                    onClick={() => setOpen(open === f.flight_id ? null : f.flight_id)}
                  >
                    <td>
                      <button
                        type="button"
                        className="link"
                        aria-expanded={open === f.flight_id}
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpen(open === f.flight_id ? null : f.flight_id);
                        }}
                      >
                        {f.flight_number}
                      </button>{" "}
                      <span className="small muted block">
                        {f.origin}→{f.destination}
                      </span>
                    </td>
                    <td>{utc(f.std)}</td>
                    <td>
                      <span className={`chip risk-${f.risk_band}`}>{BAND_LABEL[f.risk_band]}</span>
                    </td>
                    <td className="num">{pct(f.p_15)}</td>
                    <td className="num">{pct(f.p_60)}</td>
                    <td className="num">{f.planning_delay_minutes ? minutes(f.planning_delay_minutes) : "on time"}</td>
                    <td className="num">{num(f.connecting_pax)}</td>
                    <td className="num">{f.expected_misconnects.toFixed(1)}</td>
                    <td className="small">{f.reasons[0]?.text ?? "—"}</td>
                  </tr>
                  {open === f.flight_id && (
                    <tr className="detail-row">
                      <td colSpan={9}>
                        <FlightDetail flight={f} busy={busy} onAnalyse={onAnalyse} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <ModelPanel />
    </article>
  );
}

function FlightDetail({ flight, busy, onAnalyse }: { flight: RiskFlight; busy: boolean; onAnalyse: Props["onAnalyse"] }) {
  const [connections, setConnections] = useState<ConnectionRisk[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const delay = flight.planning_delay_minutes ?? 30;

  useEffect(() => {
    api
      .flightRisk(flight.flight_id)
      .then((r) => setConnections(r.connections))
      .catch((e: unknown) => setError(errorText(e, "Could not load the connections.")));
  }, [flight.flight_id]);

  return (
    <div className="risk-detail">
      <div>
        <h3>Why this flight</h3>
        {flight.reasons.length === 0 ? (
          <p className="muted">No single factor stands out.</p>
        ) : (
          <ul className="reasons">
            {flight.reasons.map((r) => (
              <li key={r.feature}>{r.text}</li>
            ))}
          </ul>
        )}
        <p className="small muted">
          Chance of a departure delay of at least 15 min {pct(flight.p_15)}, 30 min {pct(flight.p_30)}, 60 min{" "}
          {pct(flight.p_60)}, 2 h {pct(flight.p_120)}. Aircraft {flight.tail ?? "not assigned"}.
        </p>
        <button type="button" className="primary" disabled={busy} onClick={() => onAnalyse(flight.flight_id, delay)}>
          Analyse a {minutes(delay)} delay
        </button>
        <p className="small muted">Opens the delay scenario with this delay; you can change it there.</p>
      </div>
      <div>
        <h3>Connecting passengers most at risk</h3>
        {error && <p className="error">{error}</p>}
        {connections && connections.length === 0 && <p className="muted">No connecting passengers on this flight.</p>}
        {connections && connections.length > 0 && (
          <table aria-label="Connecting passengers at risk">
            <thead>
              <tr>
                <th scope="col">Passenger</th>
                <th scope="col">Onward</th>
                <th scope="col" className="num">Connection</th>
                <th scope="col" className="num">Spare after MCT</th>
                <th scope="col" className="num">Risk</th>
              </tr>
            </thead>
            <tbody>
              {connections.slice(0, 12).map((c) => (
                <tr key={`${c.pnr}:${c.passenger_id}:${c.outbound_flight_id}`}>
                  <td>
                    {c.passenger_id ?? "—"}
                    <span className="small muted block">{c.pnr}</span>
                  </td>
                  <td>
                    {c.outbound_flight_number} to {c.final_destination}
                  </td>
                  <td className="num">{minutes(c.connection_minutes)}</td>
                  <td className="num" title={c.default_mct ? "No MCT rule for this journey: default MCT used" : undefined}>
                    {c.slack_minutes} min{c.default_mct ? "*" : ""}
                  </td>
                  <td className="num">{pct(c.misconnect_risk)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {connections?.some((c) => c.default_mct) && (
          <p className="small muted">* No MCT rule for this journey at the hub: the default MCT is used.</p>
        )}
      </div>
    </div>
  );
}

function ModelPanel() {
  const [card, setCard] = useState<ModelCard | null>(null);
  useEffect(() => {
    api.modelCard().then(setCard).catch(() => setCard(null));
  }, []);
  if (!card) return null;
  const rows = (["15", "60"] as const).flatMap((t) => {
    const m = card.evaluation.metrics_by_threshold[t];
    return m ? [{ label: `${t} min`, m }] : [];
  });
  return (
    <details className="model-card">
      <summary>How good are these predictions?</summary>
      <p>
        Tested on flights the model did not see ({card.evaluation.test}). The score below (AUC) is the chance that a
        late flight is ranked above an on-time one: 0.5 is a coin toss, 1.0 is perfect. The comparison is the past
        delay rate of the same route at the same hour.
      </p>
      <div className="table-wrap">
        <table aria-label="Model test results">
          <thead>
            <tr>
              <th scope="col">Delay of at least</th>
              <th scope="col" className="num">Share of flights</th>
              <th scope="col" className="num">Model AUC</th>
              <th scope="col" className="num">Route × hour AUC</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ label, m }) => (
              <tr key={label}>
                <td>{label}</td>
                <td className="num">{pct(m.observed_rate)}</td>
                <td className="num">{m.auc?.toFixed(2) ?? "—"}</td>
                <td className="num">{m.baseline_auc?.toFixed(2) ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>Missed connections: predicted vs what happened</h3>
      <div className="table-wrap">
        <table aria-label="Missed-connection check">
          <thead>
            <tr>
              <th scope="col">Spare time after MCT</th>
              <th scope="col" className="num">Flight pairs</th>
              <th scope="col" className="num">Predicted</th>
              <th scope="col" className="num">Happened</th>
            </tr>
          </thead>
          <tbody>
            {card.evaluation.connection_backtest.map((b) => (
              <tr key={b.slack}>
                <td>{b.slack}</td>
                <td className="num">{num(b.pairs)}</td>
                <td className="num">{pct(b.predicted)}</td>
                <td className="num">{pct(b.observed)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>Assumptions</h3>
      <ul>
        {card.assumptions.map((a) => (
          <li key={a}>{a}</li>
        ))}
      </ul>
      <p className="small muted">
        {card.model}. Trained {utc(card.trained_at.replace("Z", ""))}.
      </p>
    </details>
  );
}
