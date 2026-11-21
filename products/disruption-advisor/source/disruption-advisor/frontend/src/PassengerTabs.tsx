import { type ReactNode, useState } from "react";
import type { Scenario } from "./api";
import { RewardPanel } from "./RewardPanel";

type Tab = "passengers" | "rewards";

/** One panel, two components: the passengers affected by the disruption (connections to protect or rebook) and the
 * goodwill rewards for every passenger of the flight. Both stay mounted, so nothing typed or chosen is lost on a switch. */
export function PassengerTabs({
  scenario,
  passengersLabel,
  children,
}: {
  scenario: Scenario;
  passengersLabel: string;
  children: ReactNode;
}) {
  const [tab, setTab] = useState<Tab>("passengers");
  const tabs: [Tab, string][] = [
    ["passengers", passengersLabel],
    ["rewards", "Passenger rewards / compensation"],
  ];
  return (
    <section className="passenger-panel" aria-label="Passengers">
      <div className="tabs" role="tablist" aria-label="Passenger views">
        {tabs.map(([key, label]) => (
          <button key={key} type="button" role="tab" id={`ptab-${key}`} aria-controls={`ppane-${key}`}
            aria-selected={tab === key} className={tab === key ? "tab active" : "tab"} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id="ppane-passengers" aria-labelledby="ptab-passengers" hidden={tab !== "passengers"}>
        {children}
      </div>
      <div role="tabpanel" id="ppane-rewards" aria-labelledby="ptab-rewards" hidden={tab !== "rewards"}>
        <RewardPanel scenario={scenario} />
      </div>
    </section>
  );
}
