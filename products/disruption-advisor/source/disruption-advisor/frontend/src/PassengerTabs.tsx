import { type ReactNode, useState } from "react";
import type { Scenario } from "./api";
import { RewardPanel } from "./RewardPanel";

/** Two separate collapsible banners: passengers affected by the disruption, and goodwill rewards. */
export function PassengerTabs({
  scenario,
  passengersLabel,
  children,
}: {
  scenario: Scenario;
  passengersLabel: string;
  children: ReactNode;
}) {
  const [paxOpen, setPaxOpen] = useState(false);
  const [rewardOpen, setRewardOpen] = useState(false);

  return (
    <>
      <section aria-labelledby="ptab-passengers-title">
        <h2 id="ptab-passengers-title">{passengersLabel}</h2>
        {!paxOpen ? (
          <button type="button" className="primary" onClick={() => setPaxOpen(true)}>
            Show passenger detail
          </button>
        ) : (
          <>
            <button type="button" className="link" style={{ marginBottom: "0.75rem", display: "inline-block" }}
              onClick={() => setPaxOpen(false)}>
              Hide detail
            </button>
            {children}
          </>
        )}
      </section>

      <section aria-labelledby="ptab-rewards-title">
        <h2 id="ptab-rewards-title">Passenger rewards / compensation</h2>
        <p className="small muted">Goodwill rewards and EU261 compensation for affected passengers.</p>
        {!rewardOpen ? (
          <button type="button" className="primary" onClick={() => setRewardOpen(true)}>
            Show rewards &amp; compensation
          </button>
        ) : (
          <>
            <button type="button" className="link" style={{ marginBottom: "0.75rem", display: "inline-block" }}
              onClick={() => setRewardOpen(false)}>
              Hide detail
            </button>
            <RewardPanel scenario={scenario} />
          </>
        )}
      </section>
    </>
  );
}
