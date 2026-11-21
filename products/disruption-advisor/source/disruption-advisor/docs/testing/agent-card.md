# Agent card: disruption analyst (phase 3)

Design: [ADR 0010](../architecture/adr/0010-tool-using-agent.md), [SYSTEM_ARCHITECTURE §11](../architecture/SYSTEM_ARCHITECTURE.md). Code: `backend/app/agent/` (tools, loop, planner) and `backend/app/agent_api.py`.

## What it is for
An OCC or PCU user asks the agent to look at one flight, optionally with a delay, a strategy and a note. The agent investigates with read-only engine tools. It recommends **one recovery option the engine produced**, with 2–4 reasons, the risks, and the checks the controller should make. The result is saved as a normal delay scenario. A person approves it, or overrides it with a reason. The agent never executes anything.

## What it is not for
- Deciding or executing: no tool writes data or approves anything.
- Producing numbers: every figure on screen is re-read from the engine result. The model's text may quote engine figures, but the tables never use the model's text.
- Handling personal data: tool results contain only flight facts and counts. They never contain names, PNRs, passenger IDs, document numbers or customer keys.

## How it works
| Part | Setting |
|---|---|
| Model | `claude-opus-5-5` (`AI_MODEL`), Messages API, manual tool-use loop in the API process |
| Reasoning | adaptive thinking; effort `medium` (`AGENT_EFFORT`); progress notes come from `display: "updates"` and are shown as the step notes |
| Safety net | server-side refusal fallback (`fallbacks: "default"`); a refusal, error, time-out or missing key hands over to the planner |
| Limits | 12 tool calls (`AGENT_MAX_TOOL_CALLS`), 120 s (`AGENT_TIMEOUT_SECONDS`), one run in progress per user |
| Tools | `find_flights`, `flight_status`, `aircraft_rotation`, `assess_delay`, `compare_strategies`, `passenger_impact`, `watchlist`, `submit_recommendation`; strict schemas, inputs validated in code before a tool runs |
| Final answer | `submit_recommendation` is accepted only for an option key from the last `assess_delay`; otherwise the model gets an error and can correct itself |
| Fallback | deterministic planner: flight status → assess (given delay, else the predicted planning delay, else 60 min) → compare strategies → passenger impact → recommend the chosen strategy's pick |
| Trace | every step is stored in `agent_runs.trace` (note, tool, input, one-line result, duration) and shown live |
| Cost | about USD 0.05–0.30 per run (prompt cache covers the system prompt and tools); token use is stored per run |

## Evidence
- **Tests:** `backend/tests/test_agent.py`, 10 tests, using a scripted fake Claude client. They cover:
  - the loop and the request settings: adaptive thinking with updates, effort, fallbacks, no forced tool choice;
  - privacy: every request is checked against all PNRs, customer keys, passenger IDs and document numbers in the fixture;
  - refusing an invented option, then the model correcting it;
  - planner fallback with no key, on a refusal and at the step limit (the AI's steps stay in the trace);
  - tool input validation;
  - the runs API end to end: run, trace, scenario with `result.agent`.
- **Live check (2026-11-21, prod data, real API, read-only container):**
  - flight G9519 with no delay given; the agent used the 56-minute planning delay;
  - 7 tool calls in 37 s; the prompt cache read 9.8k tokens;
  - it recommended `swap:A6-ANO` under "protect passengers", with grounded reasons and crew, aircraft and seat checks;
  - log: `execution/logs/output/T-603-live-agent-probe.log`.

## Known limits
- Output varies between runs (wording, sometimes the order of tool calls). The option list and its numbers do not.
- The agent sees the engine's assumptions: assumed costs, synthetic loyalty and special-service data, no crew legality, no revenue loss for cancellations. It is told to mention these as risks or checks where they matter.
- If the API restarts during a run, the run shows as failed and must be started again.
