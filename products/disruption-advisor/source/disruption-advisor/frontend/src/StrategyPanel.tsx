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
import { aed, minutes, num, utc } from "./format";

export const KIND_LABEL: Record<OptionKind, string> = {
  absorb: "Absorb",
  swap: "Swap",
  cancel: "Cancel",
  consolidate: "Consolidate",
  hold: "Hold connection",
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
        Each strategy picks its best option from the same list. Click a card to apply that strategy.
      </p>
      <div className="strategy-cards">
        {ordered.map((p) => {
          const o = byKey.get(p.pick);
          const isActive = p.key === active;
          return (
            <div key={p.key} data-strategy={p.key}
              className={`strategy-card${isActive ? " active" : ""}${busy ? " strategy-card-busy" : ""}`}
              role="button" tabIndex={0} aria-pressed={isActive}
              onClick={() => switchTo(p.key)}
              onKeyDown={(e) => e.key === "Enter" && switchTo(p.key)}>
              <p className="strategy-name">
                {busy === p.key ? "Switching…" : (p.label || STRATEGY_LABEL[p.key])}
                {isActive && <span className="chip chip-ok">Active</span>}
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
      {o.holds && o.holds.length > 0 && (
        <span className="small muted block">
          Holds {o.holds.map((h) => `${h.flight_number} ${h.minutes} min`).join(", ")} ·{" "}
          {num(o.holds.reduce((s, h) => s + h.connections_kept, 0))} connections kept
        </span>
      )}
      {o.cascade && o.cascade.flights_delayed > 0 && (
        <span className="small muted block" title="How far the delay spreads, including onto other aircraft">
          Knock-on: {num(o.cascade.flights_delayed)} flights on {num(o.cascade.aircraft)} aircraft
          {o.cascade.beyond_next_flight > 0 ? ` (${num(o.cascade.beyond_next_flight)} beyond the next flight)` : ""}
          {o.cascade.delay_ends ? ` · until ${utc(o.cascade.delay_ends)}` : ""}
        </span>
      )}
      {o.cancelled_flights && o.cancelled_flights.length > 0 && (
        <span className="small muted block">
          Cancels {o.cancelled_flights.map((c) => `${c.flight_number} ${c.origin}→${c.destination}`).join(", ")} ·{" "}
          {num(o.cancelled_passengers ?? 0)} passengers
        </span>
      )}
    </>
  );
}
