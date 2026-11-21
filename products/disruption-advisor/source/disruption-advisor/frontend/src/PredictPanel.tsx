import { useEffect, useState } from "react";
import { api, errorText, type LiveCurve, type PredictInputs, type PredictResult } from "./api";

const pct = (p: number): string => `${Math.round(p * 100)}%`;
const BAND_LABEL = { high: "High", medium: "Medium", low: "Low" } as const;

const BARS = ["15", "30", "60", "120"] as const;

function CurveCard({ title, curve }: { title: string; curve: LiveCurve }) {
  return (
    <section className="curve-card" aria-label={`${title} delay prediction`}>
      <h4>
        {title} <span className={`chip risk-${curve.risk_band}`}>{BAND_LABEL[curve.risk_band]}</span>
      </h4>
      <p className="small muted">{curve.mode === "planning" ? "Planning (7 days ahead)" : curve.mode}</p>
      <p className="curve-expected">
        Expected {curve.expected_minutes <= 0 ? "on time" : `${curve.expected_minutes} min late`}
      </p>
      {BARS.map((t) => (
        <div className="curve-row" key={t}>
          <span>{t === "120" ? "2 h+" : `${t}+ min`}</span>
          <span className="curve-bar" aria-hidden="true">
            <span style={{ width: `${Math.round(curve.p[t] * 100)}%` }} />
          </span>
          <span className="num">{pct(curve.p[t])}</span>
        </div>
      ))}
    </section>
  );
}

/** A delay slider with an explicit "not known" state (null): the prediction only uses what has been set. */
export function DelaySlider({ id, label, value, onChange }:
  { id: string; label: string; value: number | null; onChange: (v: number | null) => void }) {
  return (
    <div className="delay-slider">
      <label htmlFor={id}>
        {label}: <strong>{value === null ? "not known" : value < 0 ? `${-value} min early` : `${value} min`}</strong>
      </label>
      <div className="row">
        <input id={id} type="range" min={-30} max={360} step={5} value={value ?? 0}
               onChange={(e) => onChange(Number(e.target.value))} />
        {value !== null && (
          <button type="button" className="link" onClick={() => onChange(null)}>Clear</button>
        )}
      </div>
    </div>
  );
}

/** Predict departure AND arrival delay; add what is known today (inbound aircraft, own departure) to sharpen it. */
export function PredictPanel({ flightId, fixed }: { flightId: string; fixed?: { inbound: number | null; departure: number | null } }) {
  const [ownInbound, setInbound] = useState<number | null>(null);
  const [ownDeparture, setDeparture] = useState<number | null>(null);
  const inbound = fixed ? fixed.inbound : ownInbound;
  const departure = fixed ? fixed.departure : ownDeparture;
  const [result, setResult] = useState<PredictResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const body: PredictInputs = {
      inbound_arrival_delay: inbound,
      inbound_departure_delay: null,
      departure_delay: departure,
    };
    const timer = setTimeout(() => {
      setError(null);
      api
        .predict(flightId, body)
        .then(setResult)
        .catch((e: unknown) => setError(errorText(e, "Could not predict this flight.")));
    }, 300);
    return () => clearTimeout(timer);
  }, [flightId, inbound, departure]);

  const acc = result?.accuracy;
  return (
    <div className="predict-panel">
      <h3>Predict departure and arrival</h3>
      {fixed ? (
        <p className="small muted">
          Inbound delay {inbound === null ? "not set" : `${inbound} min`}, departure delay{" "}
          {departure === null ? "not set" : `${departure} min`} (set with the Advanced sliders above).
        </p>
      ) : (
        <>
          <p className="small muted">
            Add what is known today to sharpen the prediction. Leave both unset for the 7-day planning view.
          </p>
          <div className="row">
            <DelaySlider id={`inbound-${flightId}`} label="Inbound aircraft arrived late by" value={inbound} onChange={setInbound} />
            <DelaySlider id={`departure-${flightId}`} label="This flight departed / will depart late by" value={departure}
                         onChange={setDeparture} />
          </div>
        </>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      {result && (
        <div className="curve-pair">
          <CurveCard title="Departure" curve={result.departure} />
          <CurveCard title="Arrival" curve={result.arrival} />
        </div>
      )}
      {acc?.dep && acc.arr_dep && (
        <p className="small muted">
          Tested on {acc.dep.flights.toLocaleString()} unseen flights: with the inbound delay known, departure AUC (60+
          min) is {acc.dep["60"].auc} (planning only {acc.dep["60"].planning_auc}); with the departure delay known,
          arrival AUC (60+ min) is {acc.arr_dep["60"].auc} (planning only {acc.arr_dep["60"].planning_auc}).
        </p>
      )}
    </div>
  );
}

/** One line under a search result: departure and arrival chance of a 60+ minute delay for the Advanced inputs. */
export function RowPredict({ flightId, inbound, departure }:
  { flightId: string; inbound: number | null; departure: number | null }) {
  const [result, setResult] = useState<PredictResult | null | "none">(null);
  useEffect(() => {
    let live = true;
    const timer = setTimeout(() => {
      api
        .predict(flightId, { inbound_arrival_delay: inbound, inbound_departure_delay: null, departure_delay: departure })
        .then((r) => live && setResult(r))
        .catch(() => live && setResult("none"));
    }, 300);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [flightId, inbound, departure]);
  if (result === null) return <span className="small muted block">Predicting…</span>;
  if (result === "none") return <span className="small muted block">No prediction for this flight</span>;
  const part = (title: string, c: LiveCurve) =>
    `${title} ${c.expected_minutes <= 0 ? "on time" : `+${c.expected_minutes} min`}, 60+ min ${pct(c.p["60"])}`;
  // A departure delay that is set is a fact, not a forecast: show it, and predict the arrival from it.
  const dep = departure === null ? part("Departure", result.departure) : `Departure ${departure} min (set)`;
  return (
    <span className="small block row-predict">
      {dep} · {part("Arrival", result.arrival)}
      <span className="muted"> ({result.arrival.mode === "planning" ? "planning" : "live"})</span>
    </span>
  );
}
