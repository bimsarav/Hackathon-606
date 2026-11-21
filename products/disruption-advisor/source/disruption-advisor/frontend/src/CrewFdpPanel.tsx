import { useEffect, useState } from "react";
import { api, type CrewFdp, ApiError } from "./api";
import { num } from "./format";

const CREW_TYPE: Record<string, string> = {
  CP: "Captain", FO: "First officer", SO: "Second officer", CS: "Senior cabin crew", CC: "Cabin crew",
};

/** Crew FDP analysis from the roster: headroom to the maximum FDP and the effect of extra delay. */
export function CrewFdpPanel() {
  const [data, setData] = useState<CrewFdp | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    api.crewFdp()
      .then(setData)
      .catch((e: unknown) => setMissing(e instanceof ApiError ? e.problem.status === 404 : true));
  }, []);

  if (missing) return null;
  if (!data) return <p className="status">Loading crew FDP…</p>;
  const s = data.summary;
  const pilots = data.by_crew_type.filter((r) => ["CP", "FO"].includes(r.crew_type));
  const tightestPilots = pilots.length ? Math.min(...pilots.map((r) => r.left_p5)) : null;

  return (
    <section className="result crew-fdp" aria-labelledby="crew-fdp-title" style={{ marginTop: "2rem" }}>
      <header className="result-head">
        <p className="eyebrow">Crew flight duty period</p>
        <h2 id="crew-fdp-title">Crew FDP headroom</h2>
        <p className="muted small">
          {num(s.duties)} G9 crew duties, {data.period.first.slice(0, 10)} to {data.period.last.slice(0, 10)} ·{" "}
          {num(data.matched.in_history)} of {num(data.matched.roster_flights)} rostered flights matched to the flight
          history, {num(data.matched.in_window)} in the operating window. No crew names or IDs are kept.
        </p>
      </header>

      <div className="kpis" aria-label="Crew FDP key numbers">
        <div className="kpi">
          <span className="kpi-label">Median headroom</span>
          <span className="kpi-value">{num(s.headroom_median)} min</span>
          <span className="kpi-sub">maximum FDP − planned FDP</span>
        </div>
        <div className="kpi">
          <span className="kpi-label">Tightest 5%</span>
          <span className="kpi-value">{num(s.headroom_p5)} min</span>
          <span className="kpi-sub">
            {tightestPilots != null ? `pilots: ${num(tightestPilots)} min left after the actual duty` : "of planned duties"}
          </span>
        </div>
        <div className="kpi">
          <span className="kpi-label">Over the maximum</span>
          <span className="kpi-value">{num(s.over_max)}</span>
          <span className="kpi-sub">duties · {num(s.extended_max)} used an extended maximum</span>
        </div>
        <div className="kpi">
          <span className="kpi-label">Actual over plan</span>
          <span className="kpi-value">{s.pct_over_plan}%</span>
          <span className="kpi-sub">avg {num(s.planned_avg)} planned vs {num(s.actual_avg)} actual min</span>
        </div>
      </div>

      <h3>What extra delay does to crew duties</h3>
      <div className="table-wrap">
        <table>
          <caption className="visually-hidden">Share of duties that would pass the maximum FDP with extra delay</caption>
          <thead>
            <tr>
              <th scope="col">Extra delay</th>
              {data.extra_delay.map((r) => (
                <th key={r.extra_minutes} scope="col" className="num">+{r.extra_minutes} min</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Duties over the maximum FDP</th>
              {data.extra_delay.map((r) => (
                <td key={r.extra_minutes} className="num">{r.pct_over_max}%</td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <div className="crew-fdp-grid">
        <div className="table-wrap">
          <table>
            <caption>By crew type</caption>
            <thead>
              <tr>
                <th scope="col">Crew</th>
                <th scope="col" className="num">Duties</th>
                <th scope="col" className="num">Max FDP</th>
                <th scope="col" className="num">Tightest 5% left</th>
              </tr>
            </thead>
            <tbody>
              {data.by_crew_type.map((r) => (
                <tr key={r.crew_type}>
                  <td>{CREW_TYPE[r.crew_type] ?? r.crew_type}</td>
                  <td className="num">{num(r.duties)}</td>
                  <td className="num">{num(r.max_fdp_median)} min</td>
                  <td className="num">{num(r.left_p5)} min</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="table-wrap">
          <table>
            <caption>Margin left at the end of the duty</caption>
            <thead>
              <tr>
                <th scope="col">Left</th>
                <th scope="col" className="num">Duties</th>
                <th scope="col" className="num">Share</th>
              </tr>
            </thead>
            <tbody>
              {data.bands.map((r) => (
                <tr key={r.band}>
                  <td>{r.band}</td>
                  <td className="num">{num(r.duties)}</td>
                  <td className="num">{r.pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p className="small muted">
        In the recovery options, every delayed flight is checked against its tightest crew member's headroom (the
        roster, or for flights without one the 10th percentile of the same flight number's history, labelled
        estimated). Under {num(data.rules.tight_below_minutes)} min left is tight; past the maximum is an FDP breach,
        shown as an alert in the scenario (Crew FDPs) for crew control to review.
      </p>
    </section>
  );
}
