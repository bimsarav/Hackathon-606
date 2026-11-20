import { useEffect, useState } from "react";
import {
  api,
  type Decision,
  errorText,
  type Meta,
  type PassengerRow,
  type Scenario,
  WEIGHT_KEYS,
  type WeightKey,
  type Weights,
} from "./api";
import { minutes, num, utc } from "./format";

export function Explanation({ text, source }: { text: string; source: string }) {
  const ai = source.startsWith("ai:");
  return (
    <section className="explanation" aria-labelledby="why-title">
      <h2 id="why-title">
        Why this recommendation{" "}
        <span className={`chip ${ai ? "chip-ok" : ""}`}>{ai ? `Written by ${source.slice(3)}` : "Template text"}</span>
      </h2>
      <p>{text}</p>
      <p className="small muted">
        The numbers come from the recovery engine; the language model only words them. It never decides.
      </p>
    </section>
  );
}

/** Approve / reject with an audit trail (human in the loop). */
export function DecisionBar({ scenario, target, label, requireComment = false }:
  { scenario: Scenario; target: string; label: string; requireComment?: boolean }) {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.decisions(scenario.id).then(setDecisions).catch(() => setDecisions([]));
  }, [scenario.id]);

  async function decide(action: "APPROVE" | "REJECT") {
    setBusy(true);
    setError(null);
    try {
      const d = await api.decide(scenario.id, target, action, requireComment ? `OVERRIDE: ${comment}` : comment);
      setDecisions((current) => [...current, d]);
      setComment("");
    } catch (e: unknown) {
      setError(errorText(e, "Could not record the decision."));
    } finally {
      setBusy(false);
    }
  }

  const mine = decisions.filter((d) => d.target === target);
  return (
    <div className="decision">
      <div className="decision-row">
        <label htmlFor={`comment-${target}`} className="visually-hidden">
          Comment for {label}
        </label>
        <input id={`comment-${target}`} placeholder={requireComment ? "Reason for choosing this option (required)" : "Comment (optional)"}
          value={comment} maxLength={980} onChange={(e) => setComment(e.target.value)} />
        <button type="button" className="approve" disabled={busy || (requireComment && comment.trim() === "")}
          onClick={() => decide("APPROVE")}>
          Approve {label}
        </button>
        <button type="button" className="reject" disabled={busy} onClick={() => decide("REJECT")}>
          Reject
        </button>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {mine.length > 0 && (
        <ul className="audit">
          {mine.map((d) => (
            <li key={d.id}>
              <span className={d.action === "APPROVE" ? "chip chip-ok" : "chip chip-bad"}>{d.action}</span> by {d.decided_by},{" "}
              {utc(d.decided_at)}
              {d.comment && <> · “{d.comment}”</>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function WeightsPanel({ meta, scenario, onUpdate }: { meta: Meta; scenario: Scenario; onUpdate: (s: Scenario) => void }) {
  const [weights, setWeights] = useState<Weights>(scenario.weights);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setWeights(scenario.weights), [scenario.weights]);

  async function rerun() {
    setBusy(true);
    setError(null);
    try {
      onUpdate(await api.reprioritise(scenario.id, weights));
    } catch (e: unknown) {
      setError(errorText(e, "Could not re-run the ranking."));
    } finally {
      setBusy(false);
    }
  }

  const changed = WEIGHT_KEYS.some((k) => weights[k] !== scenario.weights[k]);
  return (
    <section className="weights" aria-labelledby="weights-title">
      <h2 id="weights-title">Priority weights (what-if)</h2>
      <p className="small muted">
        Weights only order passengers inside a tier. Mandated care (special assistance, infants)
        and urgency always come first, and non-revenue passengers always come last.
      </p>
      <div className="weight-grid">
        {WEIGHT_KEYS.map((k: WeightKey) => (
          <div key={k} className="field">
            <label htmlFor={`w-${k}`}>
              {meta.weight_labels[k]} <strong>{weights[k]}</strong>
            </label>
            <input id={`w-${k}`} type="range" min={0} max={50} step={5} value={weights[k]}
              onChange={(e) => setWeights({ ...weights, [k]: Number(e.target.value) })} />
          </div>
        ))}
      </div>
      <div className="row">
        <button type="button" className="primary" disabled={busy || !changed} onClick={rerun}>
          {busy ? "Re-ranking…" : "Re-run with these weights"}
        </button>
        <button type="button" disabled={busy} onClick={() => setWeights(meta.default_weights)}>
          Reset to defaults
        </button>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

const TIER_LABEL: Record<number, string> = { 1: "Care", 2: "Urgent", 3: "Standard" };

export function PassengerTable({ scenario, rows, meta }: { scenario: Scenario; rows: PassengerRow[]; meta: Meta }) {
  const [open, setOpen] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const PAGE = 30;
  const visible = showAll ? rows : rows.slice(0, PAGE);
  const [drafts, setDrafts] = useState<Record<string, { text: string; source: string } | string>>({});

  async function draft(key: string) {
    setDrafts((d) => ({ ...d, [key]: "Drafting…" }));
    try {
      const m = await api.message(scenario.id, key);
      setDrafts((d) => ({ ...d, [key]: m }));
    } catch (e: unknown) {
      setDrafts((d) => ({ ...d, [key]: errorText(e, "Could not draft the message.") }));
    }
  }

  if (rows.length === 0) return <p className="muted">No passengers need re-accommodation.</p>;
  return (
    <div className="table-wrap">
      <table className="pax">
        <caption className="visually-hidden">Passengers in priority order</caption>
        <thead>
          <tr>
            <th scope="col">#</th>
            <th scope="col">Passenger</th>
            <th scope="col">Tier</th>
            <th scope="col">Score</th>
            <th scope="col">Profile</th>
            <th scope="col">Recommended</th>
            <th scope="col">
              <span className="visually-hidden">Details</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {visible.map((p) => {
            const key = `${p.pnr}:${p.customer_key}`;
            const d = drafts[p.customer_key];
            return [
              <tr key={key} className={p.assigned_flight_id ? "" : "unprotected"}>
                <td className="num">{p.rank}</td>
                <td>
                  <strong>{p.name}</strong>
                  <span className="small muted block">
                    {p.pnr} · {p.route}
                    {p.pnr_size > 1 ? ` · party of ${p.pnr_size}` : ""}
                  </span>
                </td>
                <td>
                  <span className={`tier tier-${p.tier}`}>{p.non_revenue ? "Non-rev" : TIER_LABEL[p.tier]}</span>
                  {p.ssr && (
                    <span className="chip small" title={p.ssr_source === "synthetic" ? "Synthetic special-service code" : "From the booking data"}>
                      {p.ssr}
                      {p.ssr_source === "synthetic" ? "*" : ""}
                    </span>
                  )}
                </td>
                <td>
                  <span className="score">
                    <span className="score-bar" style={{ width: `${Math.min(p.score, 100)}%` }} />
                    <span className="score-num">{p.score}</span>
                  </span>
                </td>
                <td className="small">
                  {p.loyalty_tier ? `${p.loyalty_tier}*` : "Not a member"} · {p.frequency ?? "—"}
                  <span className="block muted">
                    {p.fare_family ?? "—"}* · fare {num(Math.round(p.fare))} · extras {num(Math.round(p.ancillaries))}
                  </span>
                </td>
                <td>
                  {p.assigned_flight_id ? (
                    <>
                      <strong>{p.assigned_flight}</strong> {utc(p.new_departure)}
                      <span className="small muted block">
                        {p.care?.wait_minutes != null ? `waits ${minutes(p.care.wait_minutes)} · ` : ""}
                        arrives {minutes(p.arrival_delay_minutes)} later
                        {p.onward_ok === false ? " · onward connection lost" : ""}
                        {p.split ? " · group split" : ""}
                      </span>
                    </>
                  ) : (
                    <span className="unprotected-label">No seat within 24 h: next day</span>
                  )}
                  {p.care && (
                    <span className="care block">
                      <span className="small">Care: <strong>{p.care.summary}</strong></span>
                      {p.care.refund_option && <span className="small block muted">Option: refund + free return, or date change</span>}
                      {p.care.flags.map((f) => (
                        <span key={f} className="flag small block">⚑ {f}</span>
                      ))}
                    </span>
                  )}
                </td>
                <td>
                  <button type="button" className="link" aria-expanded={open === key} onClick={() => setOpen(open === key ? null : key)}>
                    {open === key ? "Hide" : "Why & message"}
                  </button>
                </td>
              </tr>,
              open === key && (
                <tr key={`${key}-detail`} className="detail">
                  <td colSpan={7}>
                    <p>{p.reason}</p>
                    <ul className="contrib">
                      {Object.entries(p.contributions).map(([k, v]) => (
                        <li key={k}>
                          {meta.weight_labels[k as WeightKey]}: <strong>+{v}</strong>
                        </li>
                      ))}
                    </ul>
                    <p className="small muted">{p.assignment_reason}</p>
                    <div className="message">
                      <p className="small">
                        <strong>Message draft</strong>
                        {typeof d === "object" ? ` (${d.source.startsWith("ai:") ? `written by ${d.source.slice(3)}` : "template"})` : " (template)"}
                      </p>
                      <p>{typeof d === "object" ? d.text : typeof d === "string" ? d : p.message}</p>
                      <button type="button" onClick={() => draft(p.customer_key)}>
                        Personalise with AI
                      </button>
                    </div>
                  </td>
                </tr>
              ),
            ];
          })}
        </tbody>
      </table>
      {rows.length > PAGE && (
        <button type="button" className="link" onClick={() => setShowAll(!showAll)}>
          {showAll ? `Show the first ${PAGE} only` : `Show all ${rows.length} passengers`}
        </button>
      )}
      <p className="small muted">* synthetic value (not supplied in the airline extracts)</p>
    </div>
  );
}

export function Assumptions({ items }: { items: string[] }) {
  return (
    <details className="assumptions">
      <summary>Assumptions and data notes</summary>
      <ul>
        {items.map((a) => (
          <li key={a}>{a}</li>
        ))}
      </ul>
    </details>
  );
}
