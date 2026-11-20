# ADR-0006: OR-Tools CP-SAT for seat-limited re-accommodation

- **Status:** Accepted (2026-11-20)
- **Context:** When a flight is cancelled and alternatives have fewer seats than passengers, passengers must be assigned by priority. UC5 requires families and groups to be kept together, passenger rights to be respected independently of commercial scores, and the reasoning to be explainable.
- **Decision:** Model the assignment as a 0/1 integer programme solved with Google OR-Tools CP-SAT (`app/engine/rebooking.py`):
  - one variable per (PNR group, alternative flight);
  - at most one flight per group;
  - seats per flight no more than its available seats;
  - the objective uses widely separated tier values (100,000 / 5,000 / 200) plus the 0–100 score, minus lateness and lost-onward-connection penalties.
- **Alternatives:**
  - A greedy fill by rank: can strand a family or waste seats.
  - PuLP/HiGHS: fine, but CP-SAT has better integer performance and is Apache-2.0 licensed.
  - A learned policy: no training data, and no guarantees.
- **Consequences:**
  - Proven optimal plans in under a second for real cases (147 passengers / 60 seats); a 5 s time limit.
  - Groups larger than any free block are split and reported.
  - ortools 9.15 ships Python 3.14 wheels.
