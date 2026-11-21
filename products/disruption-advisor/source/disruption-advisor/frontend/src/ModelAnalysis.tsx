import { useEffect, useState } from "react";
import {
  api,
  type ArrivalMetrics,
  type CascadeCheck,
  type Classification,
  type DocBlock,
  errorText,
  type ModelDocs,
  type ModelMetrics,
  type ReliabilityBin,
  type RewardModelCard,
  type RollingFold,
  type TestDataStatus,
} from "./api";
import { num } from "./format";

const pct = (v: number | null | undefined, digits = 1) => (v == null ? "—" : `${(v * 100).toFixed(digits)}%`);
const f3 = (v: number | null | undefined) => (v == null ? "—" : v.toFixed(3));

/** **bold** and `code` of the bundled write-ups. */
function Md({ text }: { text: string }) {
  return (
    <>
      {text.split(/(\*\*[^*]+\*\*|`[^`]+`)/).map((part, i) =>
        part.startsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong>
          : part.startsWith("`") ? <code key={i}>{part.slice(1, -1)}</code>
          : <span key={i}>{part}</span>,
      )}
    </>
  );
}

export function Blocks({ blocks }: { blocks: DocBlock[] }) {
  return (
    <>
      {blocks.map((b, i) => {
        if (b.type === "title") return null; // the section label is the title
        if (b.type === "heading") return <h3 key={i}>{b.text}</h3>;
        if (b.type === "paragraph") return <p key={i} className="small"><Md text={b.text} /></p>;
        if (b.type === "quote") return <p key={i} className="small note"><Md text={b.text} /></p>;
        if (b.type === "bullets")
          return (
            <ul key={i} className="small">
              {b.items.map((it, j) => <li key={j}><Md text={it} /></li>)}
            </ul>
          );
        if (b.type !== "table") return null;
        return (
          <table key={i} className="model-table">
            <thead><tr>{b.header.map((h, j) => <th key={j}>{h}</th>)}</tr></thead>
            <tbody>
              {b.rows.map((r, j) => (
                <tr key={j}>{r.map((c, k) => (k === 0 ? <th scope="row" key={k}><Md text={c} /></th> : <td key={k} className="num"><Md text={c} /></td>))}</tr>
              ))}
            </tbody>
          </table>
        );
      })}
    </>
  );
}

export function Calibration({ bins, title }: { bins: ReliabilityBin[]; title: string }) {
  return (
    <>
      <p className="small muted">{title}</p>
      <table className="model-table" aria-label="Calibration">
        <thead><tr><th>Predicted chance</th><th>Flights</th><th>Average predicted</th><th>Actually happened</th><th>Difference</th></tr></thead>
        <tbody>
          {bins.map((b) => (
            <tr key={b.from}>
              <th scope="row">{pct(b.from, 0)} to {pct(b.to, 0)}</th>
              <td className="num">{num(b.flights)}</td>
              <td className="num">{pct(b.predicted)}</td>
              <td className="num">{pct(b.observed)}</td>
              <td className={`num ${b.predicted - b.observed > 0.05 ? "text-bad" : ""}`}>
                {b.predicted - b.observed >= 0 ? "+" : ""}{((b.predicted - b.observed) * 100).toFixed(1)} pp
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export function Cutoffs({ all }: { all: Record<string, Classification> }) {
  return (
    <>
      <p className="small muted">
        What happens if a flight is flagged when its chance reaches a cut-off: how many flagged flights were really late
        (precision), how many late flights were caught (recall), and the true and false alarms behind them.
      </p>
      {Object.entries(all).map(([key, c]) => (
        <div key={key}>
          <h3>{key.replace("_", " +").replace(/^./, (m) => m.toUpperCase())} min</h3>
          <table className="model-table" aria-label={`Operating points ${key}`}>
            <thead>
              <tr><th>Rule</th><th>True alarms</th><th>False alarms</th><th>Missed</th><th>Correct all-clear</th><th>Precision</th><th>Recall</th><th>F1</th></tr>
            </thead>
            <tbody>
              {c.operating_points.map((p) => (
                <tr key={p.label}>
                  <th scope="row">{p.label}</th>
                  <td className="num">{num(p.true_positive)}</td><td className="num">{num(p.false_positive)}</td>
                  <td className="num">{num(p.false_negative)}</td><td className="num">{num(p.true_negative)}</td>
                  <td className="num">{pct(p.precision)}</td><td className="num">{pct(p.recall)}</td><td className="num">{f3(p.f1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {c.top_10_percent && (
            <p className="small">
              The 10% of flights with the highest chance: {pct(c.top_10_percent.late_rate)} were late, against{" "}
              {pct(c.top_10_percent.overall_rate)} overall ({c.top_10_percent.lift?.toFixed(1) ?? "—"}× more).
            </p>
          )}
          <details>
            <summary className="small">Every cut-off from {pct(c.sweep[0]?.cutoff, 0)} to {pct(c.sweep[c.sweep.length - 1]?.cutoff, 0)}</summary>
            <table className="model-table" aria-label={`Cut-off sweep ${key}`}>
              <thead><tr><th>Cut-off</th><th>Precision</th><th>Recall</th><th>F1</th><th>Share flagged</th></tr></thead>
              <tbody>
                {c.sweep.map((s) => (
                  <tr key={s.cutoff}>
                    <th scope="row">{pct(s.cutoff, 0)}</th>
                    <td className="num">{pct(s.precision)}</td><td className="num">{pct(s.recall)}</td>
                    <td className="num">{f3(s.f1)}</td><td className="num">{pct(s.flagged_share)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </div>
      ))}
    </>
  );
}

export function Monthly({ folds }: { folds: RollingFold[] }) {
  const cell = (fold: RollingFold, t: string) => fold[t] as ModelMetrics | undefined;
  return (
    <>
      <p className="small muted">
        Each month is predicted by a model trained only on the months before it, so this shows how well the approach
        holds up as the seasons change. AUC is the ranking quality (0.5 = chance); the baseline is the route × hour rate.
      </p>
      <table className="model-table" aria-label="Month by month">
        <thead>
          <tr><th>Month</th><th>Train flights</th><th>Test flights</th><th>AUC +15</th><th>Baseline +15</th><th>AUC +60</th><th>Baseline +60</th><th>Brier +60</th><th>Climatology +60</th></tr>
        </thead>
        <tbody>
          {folds.map((f) => (
            <tr key={f.month}>
              <th scope="row">{f.month}</th>
              <td className="num">{num(f.train_flights)}</td><td className="num">{num(f.test_flights)}</td>
              <td className="num">{f3(cell(f, "15")?.auc)}</td><td className="num">{f3(cell(f, "15")?.baseline_auc)}</td>
              <td className="num">{f3(cell(f, "60")?.auc)}</td><td className="num">{f3(cell(f, "60")?.baseline_auc)}</td>
              <td className="num">{f3(cell(f, "60")?.brier)}</td><td className="num">{f3(cell(f, "60")?.climatology_brier)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export function Arrival({ metrics }: { metrics: Record<string, ArrivalMetrics> }) {
  return (
    <>
      <p className="small muted">
        A second model predicts the arrival delay of the inbound flight. Together with the onward flight's departure model
        it gives each connecting passenger's missed-connection risk.
      </p>
      <table className="model-table" aria-label="Arrival model">
        <thead><tr><th>Arrival delay of at least</th><th>Happened in the test weeks</th><th>AUC</th><th>Brier</th><th>Brier of the plain average</th></tr></thead>
        <tbody>
          {Object.entries(metrics).map(([t, m]) => (
            <tr key={t}>
              <th scope="row">+{t} min</th>
              <td className="num">{pct(m.observed_rate)}</td><td className="num">{f3(m.auc)}</td>
              <td className="num">{f3(m.brier)}</td><td className="num">{f3(m.climatology_brier)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export function CascadeSummary() {
  const [data, setData] = useState<CascadeCheck | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.cascade().then(setData).catch((e) => setError(errorText(e, "Could not load the cascade check.")));
  }, []);
  if (error) return <p className="error" role="alert">{error}</p>;
  if (!data) return <p className="status">Loading…</p>;
  const k = data.kpis;
  return (
    <>
      <p className="small">
        <strong>Rule under test:</strong> {data.formula}. <span className="muted">{data.definition}</span>
      </p>
      <table className="model-table" aria-label="Cascade check summary">
        <tbody>
          <tr><th scope="row">Period</th><td className="num">{data.from ?? "—"} to {data.to ?? "—"}</td></tr>
          <tr><th scope="row">Aircraft pairs with a predicted knock-on</th><td className="num">{num(k.pairs)}</td></tr>
          <tr><th scope="row">Average error (actual minus formula)</th><td className="num">{k.mean_delta == null ? "—" : `${k.mean_delta} min`}</td></tr>
          <tr><th scope="row">Within ±15 min of the formula</th><td className="num">{num(k.within_15)} ({pct(k.within_15_share)})</td></tr>
          <tr><th scope="row">Within ±30 min</th><td className="num">{num(k.within_30)} ({pct(k.within_30_share)})</td></tr>
          <tr><th scope="row">Formula too low / too high by over 15 min</th><td className="num">{num(k.underestimates)} / {num(k.overestimates)}</td></tr>
          <tr><th scope="row">Left out as extreme ({data.excluded_rule})</th><td className="num">{num(data.excluded.length)}</td></tr>
        </tbody>
      </table>
      <p className="small muted">The distribution chart and the full pair list are on the Delay Watchlist page.</p>
    </>
  );
}

export function RewardModel({ docs }: { docs: ModelDocs | null }) {
  const [card, setCard] = useState<RewardModelCard | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.rewardModel().then(setCard).catch((e) => setError(errorText(e, "No reward model card yet.")));
  }, []);
  if (error) return <p className="error" role="alert">{error}</p>;
  if (!card) return <p className="status">Loading…</p>;
  const m = card.metrics_on_held_out_passengers;
  return (
    <>
      {card.synthetic_training_data && <p className="note small" role="note"><strong>Synthetic data.</strong> {card.warning}</p>}
      <p className="small muted">
        LightGBM acceptance model · trained {card.trained_at.slice(0, 10)}
        {card.versions?.lightgbm && <> · LightGBM {card.versions.lightgbm}</>} · {num(card.history.offers)} simulated offers
        for {num(card.history.passengers)} passengers ({num(card.history.train_offers)} train, {num(card.history.test_offers)} test, whole passengers kept apart).
      </p>
      <table className="model-table" aria-label="Reward model scores">
        <thead><tr><th>On held-out passengers</th><th>AUC</th><th>Brier</th></tr></thead>
        <tbody>
          <tr><th scope="row">Trained model</th><td className="num">{f3(m.auc)}</td><td className="num">{f3(m.brier)}</td></tr>
          <tr><th scope="row">Average per reward type (baseline)</th><td className="num">{f3(m.baseline_type_average.auc)}</td><td className="num">{f3(m.baseline_type_average.brier)}</td></tr>
          <tr><th scope="row">Proxy rules (first version)</th><td className="num">{f3(m.baseline_proxy_rules.auc)}</td><td className="num">—</td></tr>
        </tbody>
      </table>
      <p className="small">Overall acceptance in the test set: {pct(m.observed_acceptance_rate)}.</p>
      <table className="model-table" aria-label="By reward type">
        <thead><tr><th>Reward type</th><th>Offers</th><th>Acceptance</th><th>AUC</th></tr></thead>
        <tbody>
          {Object.entries(m.by_reward_type).map(([type, r]) => (
            <tr key={type}><th scope="row">{type}</th><td className="num">{num(r.offers)}</td><td className="num">{pct(r.acceptance_rate)}</td><td className="num">{f3(r.auc)}</td></tr>
          ))}
        </tbody>
      </table>
      {m.reliability && m.reliability.length > 0 && <Calibration bins={m.reliability} title="Predicted acceptance against what the simulation produced (held-out passengers)." />}
      <h3>Behaviour built into the simulation</h3>
      <ul className="small">{card.assumed_behaviour.map((a) => <li key={a}>{a}</li>)}</ul>
      <p className="small muted">Inputs ({card.features.length}): {card.features.join(", ")}.</p>
      {docs && (
        <>
          <h2>Model comparison and tuning</h2>
          <Blocks blocks={docs.reward_selection} />
        </>
      )}
    </>
  );
}

export function TestDataScoring() {
  const [status, setStatus] = useState<TestDataStatus | null>(null);
  useEffect(() => {
    api.testData().then(setStatus).catch(() => setStatus(null));
  }, []);
  return (
    <>
      <p className="small">
        Flights uploaded on the Test data page are <strong>scored, never trained on</strong>. The saved delay model
        (written at ingest) predicts them from the live history: the aircraft's previous flight, the route's recent delay
        rate, the month. The reward model ranks reward options for their passengers as it does for real ones. Nothing is
        retrained, so a test sheet cannot make the model look better than it is.
      </p>
      <p className="small">
        The sheets hold no actual delays, so there is no accuracy figure for uploaded flights yet: only predictions.
        Routes without history in the live data get a risk figure with little behind it.
      </p>
      {status?.loaded ? (
        <p className="small">
          Loaded now: {status.counts?.flights} flights, {status.counts?.passengers} passengers;{" "}
          {status.risk && status.risk.scored > 0
            ? `${status.risk.scored} scored with the saved model.`
            : `not scored (${status.risk?.reason ?? "unknown reason"}).`}
        </p>
      ) : (
        <p className="small muted">No test data is loaded right now.</p>
      )}
    </>
  );
}
