# ADR-0010: Passenger reward recommendation with proxy preferences and a budget

- **Status:** Accepted (2026-11-21, phase 5 approved by the user)
- **Context:** After a disruption the airline can offer goodwill rewards. The planner needs a defensible way to decide who gets what within a budget. The data has passenger value signals (loyalty, frequency, fare, ancillaries) but no record of which rewards customers accepted, so a trained preference model is not possible yet.
- **Decision:**
  - **Severity x value -> target amount -> reward type -> budget fit**, as in `docs/architecture/REWARDS_DESIGN.md`.
  - **Preferences:** first by proxy rules (meal and seat bought, sales channel, fare family, loyalty, frequency, family booking); then (2026-11-21, the user allowed synthetic data) by a **LightGBM acceptance model trained on simulated redemption history**, with the proxy rules kept as the fallback and as a baseline. Everything derived from the simulated history is labelled synthetic.
  - **Budget fitting by marginal downgrade:** deterministic, explainable, fast for hundreds of passengers; no solver needed.
  - **Recommend-only:** the plan is computed on request (not stored); approval is recorded through the existing decisions audit log. Nothing is sent to passengers.
- **Alternatives considered:**
  - **Trained acceptance model:** the right long-term answer, but there is no redemption data. The rules replace it behind the same interface when data exists.
  - **CP-SAT allocation:** exact for linear utilities, but the concave utility and the downgrade ladder are simpler and easier to explain greedily.
  - **Reward by loyalty tier only:** ignores how badly the passenger was affected.
- **Consequences:**
  - Catalogue values, severity weights and proxy rules are assumptions to confirm with the airline; they live in `RewardRules`.
  - Statutory care stays outside the goodwill budget so a budget can never reduce a passenger's rights.
