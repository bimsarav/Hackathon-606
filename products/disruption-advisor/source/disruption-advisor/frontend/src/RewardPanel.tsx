import { type FormEvent, useState } from "react";
import { api, errorText, type RewardPlan, type Scenario } from "./api";
import { aed, num, utc } from "./format";
import { DecisionBar, TIER_LABEL } from "./Shared";

const TYPE_ICON: Record<string, string> = { MEAL: "Meal", VOUCHER: "Voucher", LOUNGE: "Lounge", MILES: "Miles", TICKET: "Ticket" };

/** Phase 5: goodwill reward plan for the passengers of the flight, within a budget. Recommend-only. */
export function RewardPanel({ scenario }: { scenario: Scenario }) {
  const [budget, setBudget] = useState("5000");
  const [plan, setPlan] = useState<RewardPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

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
              <strong>{num(plan.rewarded)}</strong> of {num(plan.passengers)} passengers on the passenger list rewarded
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
              <table className="pax">
                <caption className="visually-hidden">Recommended goodwill reward per passenger</caption>
                <thead>
                  <tr>
                    <th scope="col">#</th>
                    <th scope="col">Passenger</th>
                    <th scope="col">Recommended reward</th>
                    <th scope="col" className="num">Reward value (AED)</th>
                    <th scope="col">
                      <span className="visually-hidden">Details</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((r, i) => {
                    const key = `${r.pnr}:${r.customer_key}`;
                    return [
                      <tr key={key}>
                        <td className="num">{i + 1}</td>
                        <td>
                          <strong>{r.passenger_id ?? r.customer_key}</strong>
                          <span className="small muted block">
                            {r.pnr} · {r.route}
                          </span>
                        </td>
                        <td>
                          <strong>{r.reward?.label}</strong>
                          <span className="small muted block">{r.reward?.detail}</span>
                        </td>
                        <td className="num">
                          <strong>{num(r.reward?.cost_aed ?? 0)}</strong>
                        </td>
                        <td>
                          <button type="button" className="link" aria-expanded={open === key} onClick={() => setOpen(open === key ? null : key)}>
                            {open === key ? "Hide" : "More data"}
                          </button>
                        </td>
                      </tr>,
                      open === key && (
                        <tr key={`${key}-detail`} className="detail">
                          <td colSpan={5}>
                            <p>
                              <span className={`tier tier-${r.tier}`}>{TIER_LABEL[r.tier] ?? r.tier}</span> Disruption severity{" "}
                              <span className="score">
                                <span className="score-bar" style={{ width: `${Math.min(r.severity, 100)}%` }} />
                                <span className="score-num">{r.severity}</span>
                              </span>{" "}
                              · passenger value <strong>{r.value}</strong>/100 · target <strong>{aed(r.target_aed)}</strong>
                              {r.reward?.acceptance != null && (
                                <>
                                  {" "}
                                  · chance they accept <strong>{Math.round(r.reward.acceptance * 100)}%</strong>
                                </>
                              )}
                            </p>
                            <ul className="contrib">
                              {r.severity_reasons.map((x) => (
                                <li key={x}>{x}</li>
                              ))}
                            </ul>
                            <p className="small">
                              <strong>Upcoming:</strong>{" "}
                              {r.upcoming && r.upcoming.count > 0
                                ? [
                                    r.upcoming.connection ? "a connecting flight" : null,
                                    r.upcoming.return ? "a return flight booked" : null,
                                    `${r.upcoming.count} later flight${r.upcoming.count > 1 ? "s" : ""}`,
                                  ]
                                    .filter(Boolean)
                                    .join(", ") +
                                  (r.upcoming.next ? `. Next: ${r.upcoming.next.flight_number} ${r.upcoming.next.route}, ${utc(r.upcoming.next.std)}` : "")
                                : "no later flights on this booking"}
                              .
                            </p>
                            <p className="small muted">
                              Why this reward: {r.why.length ? r.why.join(", ") : "best fit for the amount"}.
                              {r.preferred.length > 0 && ` Likeliest to take: ${r.preferred.map((x) => `${x.label} ${Math.round(x.score * 100)}%`).join(", ")}.`}
                              {r.downgraded_for_budget ? " Scaled down to fit the budget." : ""}
                            </p>
                          </td>
                        </tr>
                      ),
                    ];
                  })}
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
