import { useState } from "react";
import {
  api,
  type DelayResult,
  errorText,
  type OptionKind,
  type RecoveryOption,
  type Scenario,
  STRATEGY_KEYS,
  STRATEGY_LABEL,
  type StrategyKey,
  type StrategyPick,
} from "./api";
import { aed, minutes, num } from "./format";

export const KIND_LABEL: Record<OptionKind, string> = {
  absorb: "Absorb",
  swap: "Swap",
  cancel: "Cancel",
  consolidate: "Consolidate",
};

/** Passenger delay in hours (the engine sends minutes summed over passengers). */
export const paxHours = (n: number | undefined): string => `${num(Math.round((n ?? 0) / 60))} h`;

/** Phase 3 (ADR 0011): each strategy's pick side by side, with a switch for the active strategy. */
export function StrategyPanel({ scenario, result, onUpdate }:
  { scenario: Scenario; result: DelayResult; onUpdate: (s: Scenario) => void }) {
  const [busy, setBusy] = useState<StrategyKey | null>(null);
  const [error, setError] = useState<string | null>(null);
  const picks = result.strategies ?? [];
  if (picks.length === 0) return null; // scenario saved before phase 3
  const active: StrategyKey = result.strategy ?? "lowest_cost";
  const byKey = new Map(result.options.map((o) => [o.key, o]));

  async function switchTo(key: StrategyKey) {
    if (key === active || busy) return;
    setBusy(key);
    setError(null);
    try {
      onUpdate(await api.chooseStrategy(scenario.id, key));
    } catch (e: unknown) {
      setError(errorText(e, "Could not switch the strategy."));
    } finally {
      setBusy(null);
    }
  }

  const ordered = STRATEGY_KEYS.map((k) => picks.find((p) => p.key === k)).filter((p): p is StrategyPick => !!p);
  return (
    <section aria-labelledby="strategies-title" className="strategies">
      <h2 id="strategies-title">Strategies compared</h2>
      <p className="small muted">
        Each strategy picks its best option from the same list. Switching the strategy changes which option is
        recommended, not the numbers.
      </p>
      <div className="segmented" role="group" aria-label="Strategy">
        {ordered.map((p) => (
          <button key={p.key} type="button" aria-pressed={p.key === active} disabled={busy !== null}
            className={p.key === active ? "active" : ""} onClick={() => switchTo(p.key)}>
            {busy === p.key ? "Switching…" : (p.label || STRATEGY_LABEL[p.key])}
          </button>
        ))}
      </div>
      <div className="strategy-cards">
        {ordered.map((p) => {
          const o = byKey.get(p.pick);
          return (
            <div key={p.key} data-strategy={p.key} className={`strategy-card ${p.key === active ? "active" : ""}`}
              aria-current={p.key === active ? "true" : undefined}>
              <p className="strategy-name">
                {p.label || STRATEGY_LABEL[p.key]}
                {p.key === active && <span className="chip chip-ok">Active</span>}
              </p>
              <p className="strategy-pick">{o?.label ?? p.pick}</p>
              {o && <StrategyKpis option={o} />}
            </div>
          );
        })}
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

function StrategyKpis({ option: o }: { option: RecoveryOption }) {
  return (
    <dl className="strategy-kpis">
      <dt>Cost</dt>
      <dd>{aed(o.cost_aed)}</dd>
      <dt>Missed connections</dt>
      <dd>{num(o.misconnects)}</dd>
      <dt>Passengers without a seat</dt>
      <dd>{num(o.passengers_without_seat ?? 0)}</dd>
      <dt>Cancelled passengers</dt>
      <dd>{num(o.cancelled_passengers ?? 0)}</dd>
      <dt>Passenger delay</dt>
      <dd>{paxHours(o.passenger_delay_minutes)}</dd>
      <dt>Aircraft delay</dt>
      <dd>{minutes(o.total_delay_minutes)}</dd>
    </dl>
  );
}

/** Kind chip and cancelled flights for one row of the options table. */
export function OptionKindInfo({ option: o }: { option: RecoveryOption }) {
  return (
    <>
      {o.kind && <span className={`chip kind kind-${o.kind}`}>{KIND_LABEL[o.kind]}</span>}
      {o.cancelled_flights && o.cancelled_flights.length > 0 && (
        <span className="small muted block">
          Cancels {o.cancelled_flights.map((c) => `${c.flight_number} ${c.origin}→${c.destination}`).join(", ")} ·{" "}
          {num(o.cancelled_passengers ?? 0)} passengers
        </span>
      )}
    </>
  );
}
