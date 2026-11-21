import { type FormEvent, useState } from "react";
import { api, errorText, type RewardPlan, type Scenario } from "./api";
import { aed, num } from "./format";
import { DecisionBar } from "./Shared";

const TYPE_ICON: Record<string, string> = { MEAL: "Meal", VOUCHER: "Voucher", LOUNGE: "Lounge", MILES: "Miles", TICKET: "Ticket" };

/** Phase 5: goodwill reward plan for the passengers of the flight, within a budget. Recommend-only. */
export function RewardPanel({ scenario }: { scenario: Scenario }) {
  const [budget, setBudget] = useState("5000");
  const [plan, setPlan] = useState<RewardPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  async function run(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = Number(budget);
    if (!Number.isFinite(value) || value < 0) {
      setError("Enter a budget of zero or more (AED).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setPlan(await api.rewards(scenario.id, value));
    } catch (e: unknown) {
      setError(errorText(e, "Could not build the reward plan."));
    } finally {
      setBusy(false);
    }
  }

  const rows = plan ? plan.rows.filter((r) => r.reward) : [];
  const shown = showAll ? rows : rows.slice(0, 15);
  return (
    <section aria-labelledby="reward-title" className="rewards">
      <h2 id="reward-title">Passenger rewards (goodwill)</h2>
      <p className="muted small">
        Set a budget and the system recommends a reward for each passenger of the flight, by how badly they were
        affected and how valuable they are. Preferences are guessed from booking behaviour (assumption). Statutory care
        is separate and not taken from this budget. Nothing is sent to passengers.
      </p>
      <form className="reward-form" onSubmit={run}>
        <label htmlFor="reward-budget">Budget (AED)</label>
        <input id="reward-budget" type="number" min={0} step={500} value={budget} onChange={(e) => setBudget(e.target.value)} />
        <button type="submit" disabled={busy}>
          {busy ? "Working…" : "Recommend rewards"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      {plan && (
        <>
          <ul className="reward-kpis">
            <li>
              Disruption: <strong>{plan.disruption.label}</strong> ({plan.disruption.score}/100)
            </li>
            <li>
              Planned spend <strong>{aed(plan.planned_spend_aed)}</strong> of {aed(plan.budget_aed)} (left {aed(plan.left_aed)})
            </li>
            <li>
              <strong>{num(plan.rewarded)}</strong> of {num(plan.passengers)} passengers rewarded
            </li>
            <li>
              {plan.budget_covers_share >= 1
                ? "The budget covers the full recommended plan."
                : `The budget covers ${Math.round(plan.budget_covers_share * 100)}% of the full plan (${aed(plan.ideal_spend_aed)}), so rewards were scaled down.`}
            </li>
          </ul>
          {plan.preference_model && (
            <p className="small muted">
              Preferences: {plan.preference_model.kind}
              {plan.preference_model.synthetic_training_data
                ? ` trained on simulated redemption history (no real history exists; AUC ${plan.preference_model.auc}, proxy rules ${plan.preference_model.baseline_proxy_rules_auc})`
                : " (assumed rules)"}
              .
            </p>
          )}
          <p className="small">
            {Object.entries(plan.by_type).map(([k, v]) => (
              <span key={k} className="chip">
                {TYPE_ICON[k] ?? k}: {v.passengers} · {aed(v.spend_aed)}
              </span>
            ))}
          </p>
          {rows.length === 0 ? (
            <p className="muted">No passenger qualifies at this budget.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Passenger</th>
                    <th scope="col" className="num">Severity</th>
                    <th scope="col" className="num">Value</th>
                    <th scope="col">Recommended reward</th>
                    <th scope="col" className="num">AED</th>
                    <th scope="col">Why (chance they accept)</th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((r) => (
                    <tr key={`${r.pnr}-${r.customer_key}`}>
                      <td>
                        {r.passenger_id ?? r.customer_key}
                        <div className="small muted">{r.route}</div>
                      </td>
                      <td className="num" title={r.severity_reasons.join("; ")}>{r.severity}</td>
                      <td className="num">{r.value}</td>
                      <td>
                        {r.reward?.detail}
                        {r.downgraded_for_budget && <div className="small muted">scaled down to fit the budget</div>}
                      </td>
                      <td className="num">{num(r.reward?.cost_aed ?? 0)}</td>
                      <td className="small">{r.why.length ? r.why.join(", ") : "best fit for the amount"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {rows.length > 15 && (
            <button type="button" className="link" onClick={() => setShowAll(!showAll)}>
              {showAll ? "Show fewer" : `Show all ${rows.length}`}
            </button>
          )}
          {rows.length > 0 && <DecisionBar scenario={scenario} target={`rewards:${Math.round(plan.budget_aed)}`} label="reward plan" />}
          <ul className="small muted">
            {plan.assumptions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
