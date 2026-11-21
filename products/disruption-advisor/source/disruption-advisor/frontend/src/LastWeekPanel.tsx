import { useEffect, useState } from "react";
import { api, errorText, type LastWeek } from "./api";

const pct = (p: number | null | undefined): string => (p == null ? "n/a" : `${Math.round(p * 100)}%`);
const OUTCOME = {
  hit: "Predicted and late",
  false_alarm: "Flagged, not late",
  missed: "Not flagged, but late",
} as const;

/** Sidebar of the 7-day watchlist: last week's flights predicted by a model that had not seen them, against what
 * really happened. Shows how much to trust this week's watchlist. */
export function LastWeekPanel() {
  const [data, setData] = useState<LastWeek | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [show, setShow] = useState<"hit" | "missed" | "false_alarm">("hit");

  useEffect(() => {
    api
      .lastWeek()
      .then(setData)
      .catch((e: unknown) => setError(errorText(e, "Could not load the last-week check.")));
  }, []);

  const f60 = data?.flag_60;
  const rows = data?.rows.filter((r) => r.outcome === show).slice(0, 12) ?? [];
  return (
    <section className="last-week" aria-labelledby="last-week-title">
      <h2 id="last-week-title">Last week: predicted vs actual</h2>
      {error && <p className="error">{error}</p>}
      {!data && !error && <p className="muted">Checking last week…</p>}
      {data && f60 && (
        <>
          <p className="small muted">
            {data.from} to {data.to}, {data.flights} flights. Predicted by a model trained only on {data.trained_on}, so it
            had not seen them.
          </p>
          <ul className="last-week-kpis">
            <li>
              <strong>{pct(f60.accuracy)}</strong> of flights called right (late 60+ min or not)
            </li>
            <li>
              <strong>{pct(f60.recall)}</strong> of the {f60.true_positive + f60.false_negative} flights that left 60+ min late
              were flagged
            </li>
            <li>
              <strong>{pct(f60.precision)}</strong> of the {f60.true_positive + f60.false_positive} flagged flights were really
              late
            </li>
            <li>
              15+ min late: <strong>{pct(data.flag_15.accuracy)}</strong> called right at a 50% cut-off
            </li>
            <li className="muted">
              Ranking score (AUC): {data.auc_60 ?? "n/a"} for 60 min, {data.auc_15 ?? "n/a"} for 15 min
            </li>
          </ul>
          <div className="tabs" role="tablist" aria-label="Last week flights">
            {(["hit", "missed", "false_alarm"] as const).map((k) => (
              <button key={k} type="button" role="tab" aria-selected={show === k}
                className={show === k ? "tab active" : "tab"} onClick={() => setShow(k)}>
                {OUTCOME[k]}
              </button>
            ))}
          </div>
          {rows.length === 0 ? (
            <p className="muted small">None.</p>
          ) : (
            <ul className="last-week-list">
              {rows.map((r) => (
                <li key={r.flight_id}>
                  <strong>
                    {r.flight_number} {r.origin}→{r.destination}
                  </strong>
                  <span className="small muted">
                    {" "}
                    predicted {pct(r.p_60)} (60+), actual {r.actual_delay_minutes} min
                  </span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
