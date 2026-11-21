import { useEffect, useState } from "react";
import {
  type AgentNote,
  type AgentRun,
  type AgentRunRequest,
  type AgentRunSummary,
  type AgentStep,
  api,
  ApiError,
  errorText,
  type RecoveryOption,
  STRATEGY_LABEL,
  type StrategyKey,
} from "./api";
import { minutes, utc } from "./format";

const TOOL_LABEL: Record<string, string> = {
  find_flights: "Searched for flights",
  flight_status: "Checked flight status",
  aircraft_rotation: "Checked the aircraft's next flights",
  assess_delay: "Assessed the delay and the recovery options",
  compare_strategies: "Compared the strategies",
  passenger_impact: "Checked the impact on passengers",
  watchlist: "Looked at the delay watchlist",
  submit_recommendation: "Submitted its recommendation",
};

export const toolLabel = (tool: string): string => TOOL_LABEL[tool] ?? tool.replace(/_/g, " ");

/** "ai:<model>" → AI (Claude); "planner" → Rule-based planner. */
export const agentSourceLabel = (source: string | null | undefined): string =>
  source?.startsWith("ai:") ? "AI (Claude)" : source === "planner" ? "Rule-based planner" : "Agent";

const strategyLabel = (s: StrategyKey | string | null | undefined): string =>
  s ? (STRATEGY_LABEL[s as StrategyKey] ?? s) : "No preference";

/** "G9519_202611210200" → "G9519 · 21 Nov 02:00Z". */
export function flightLabel(flightId: string): string {
  const [number, stamp] = flightId.split("_");
  const m = /^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})$/.exec(stamp ?? "");
  return m ? `${number} · ${utc(`${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}`)}` : flightId;
}

/** Readable text for a failed start (409: a run is already going). */
export function agentStartError(e: unknown): string {
  if (e instanceof ApiError && e.problem.status === 409)
    return "You already have an agent run in progress. Wait for it to finish (see the Agent tab), then try again.";
  if (e instanceof ApiError && e.problem.status === 404) return "That flight is not in the operating window.";
  return errorText(e, "Could not start the agent. Try again.");
}

const STATUS_LABEL = { RUNNING: "Working…", DONE: "Done", FAILED: "Failed" } as const;
const STATUS_CHIP = { RUNNING: "chip-warn", DONE: "chip-ok", FAILED: "chip-bad" } as const;

interface Props {
  runId: string;
  /** Loads the scenario the agent produced into the scenario view. */
  onOpenScenario: (scenarioId: string) => void;
  /** Starts a new run with the same inputs (after a failure). */
  onRetry: (request: AgentRunRequest) => void;
  /** Called when the run's status is known or changes (e.g. to refresh a list of runs). */
  onStatus?: (status: AgentRun["status"]) => void;
  /** Polling interval while the run is going; injectable for tests. */
  pollMs?: number;
}

/** Phase 3 (ADR 0010): one agent run, followed live until it has a recommendation. */
export function AgentRunView({ runId, onOpenScenario, onRetry, onStatus, pollMs = 2000 }: Props) {
  const [run, setRun] = useState<AgentRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState<RecoveryOption[] | null>(null);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    setRun(null);
    setError(null);
    setOptions(null);
    const poll = async () => {
      try {
        const r = await api.agentRun(runId);
        if (stopped) return;
        setRun(r);
        setError(null);
        if (r.status === "RUNNING") timer = setTimeout(poll, pollMs);
      } catch (e: unknown) {
        if (stopped) return;
        if (e instanceof ApiError && e.problem.status === 404) {
          setError("This agent run no longer exists.");
          return;
        }
        setError(`${errorText(e, "Lost contact with the server.")} Retrying…`);
        timer = setTimeout(poll, pollMs);
      }
    };
    void poll();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, [runId, pollMs]);

  const status = run?.status;
  useEffect(() => {
    if (status) onStatus?.(status);
  }, [status, onStatus]);

  // Load the produced scenario once, so the recommendation can name the option in plain words.
  const scenarioId = run?.status === "DONE" ? run.scenario_id : null;
  useEffect(() => {
    if (!scenarioId) return;
    api
      .scenario(scenarioId)
      .then((s) => setOptions(s.result.type === "DELAY" ? s.result.options : null))
      .catch(() => setOptions(null));
  }, [scenarioId]);

  if (!run) {
    return (
      <article className="result">
        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : (
          <p className="status">Loading the agent run…</p>
        )}
      </article>
    );
  }

  const rec = run.recommendation;
  const option = rec ? options?.find((o) => o.key === rec.option_key) : undefined;
  return (
    <article className="result agent-run">
      <header className="result-head">
        <p className="eyebrow">Phase 3 · Agent</p>
        <h1>
          Agent: {flightLabel(run.flight_id)}{" "}
          <span className={`chip ${STATUS_CHIP[run.status]}`} data-status={run.status}>
            {STATUS_LABEL[run.status]}
          </span>
        </h1>
        <p className="muted">
          {run.delay_minutes ? `Delay ${minutes(run.delay_minutes)}` : "Delay: the agent uses the predicted one"} · strategy:{" "}
          {strategyLabel(run.strategy)} · started by {run.created_by}, {utc(run.created_at)}
        </p>
        {run.note && <p className="small">Your note: “{run.note}”</p>}
      </header>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <section aria-labelledby="steps-title">
        <h2 id="steps-title">What the agent did ({run.trace.length} steps)</h2>
        <p className="small muted">
          The agent only reads data through the recovery engine. It changes nothing and approves nothing.
        </p>
        <StepList steps={run.trace} />
        {run.status === "RUNNING" && (
          <p className="status" aria-live="polite">
            Working… this takes up to a minute with the AI, a few seconds with the rule-based planner.
          </p>
        )}
      </section>

      {run.status === "FAILED" && (
        <section aria-labelledby="failed-title">
          <h2 id="failed-title">The agent could not finish</h2>
          <p className="error" role="alert">
            {run.error ?? "The run failed."}
          </p>
          <button type="button" className="primary"
            onClick={() => onRetry({ flight_id: run.flight_id, delay_minutes: run.delay_minutes, strategy: run.strategy,
              note: run.note })}>
            Try again
          </button>
        </section>
      )}

      {run.status === "DONE" && rec && (
        <section aria-labelledby="rec-title" className="agent-panel">
          <h2 id="rec-title">
            Recommendation <span className={`chip ${run.source?.startsWith("ai:") ? "chip-ok" : ""}`}>{agentSourceLabel(run.source)}</span>
          </h2>
          {run.source === "planner" && run.fallback_reason && (
            <p className="note">
              The AI could not finish ({run.fallback_reason}), so the rule-based planner answered.
            </p>
          )}
          <p className="agent-pick">
            <strong>{option?.label ?? rec.option_key}</strong>
            <span className="muted">
              {" "}
              · {strategyLabel(rec.strategy)} · delay {minutes(rec.delay_minutes)}
            </span>
          </p>
          <AgentLists reasons={rec.reasons} risks={rec.risks} checks={rec.checks} />
          {run.scenario_id && (
            <div className="row">
              <button type="button" className="primary" onClick={() => onOpenScenario(run.scenario_id as string)}>
                Open scenario to review and approve
              </button>
            </div>
          )}
          <p className="small muted">The controller approves or overrides the recommendation in the scenario.</p>
        </section>
      )}
    </article>
  );
}

function StepList({ steps }: { steps: AgentStep[] }) {
  if (steps.length === 0) return <p className="muted">No steps yet.</p>;
  return (
    <ol className="agent-steps" aria-label="Agent steps">
      {steps.map((s) => (
        <li key={s.n} className={`agent-step ${s.error ? "warn" : ""}`}>
          <span className="agent-step-n" aria-hidden="true">
            {s.n}
          </span>
          <div>
            <p className="agent-step-tool">
              <strong>{toolLabel(s.tool)}</strong>
              {s.error && <span className="chip chip-warn">Problem</span>}
              <span className="small muted"> · {s.ms < 1000 ? `${s.ms} ms` : `${(s.ms / 1000).toFixed(1)} s`}</span>
            </p>
            {s.note && <p className="agent-step-note">{s.note}</p>}
            <p className="small muted agent-step-summary">{s.summary}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

function AgentLists({ reasons, risks, checks }: { reasons: string[]; risks: string[]; checks: string[] }) {
  const groups: [string, string[]][] = [
    ["Reasons", reasons],
    ["Risks", risks],
    ["Checks before approving", checks],
  ];
  return (
    <div className="agent-lists">
      {groups
        .filter(([, items]) => items.length > 0)
        .map(([title, items]) => (
          <div key={title}>
            <h3>{title}</h3>
            <ul className="reasons">
              {items.map((i) => (
                <li key={i}>{i}</li>
              ))}
            </ul>
          </div>
        ))}
    </div>
  );
}

/** The agent's recommendation as shown in the delay view of the scenario it produced. */
export function AgentRecommendationPanel({ agent, optionLabel }: { agent: AgentNote; optionLabel: string }) {
  return (
    <section aria-labelledby="agent-title" className="agent-panel">
      <h2 id="agent-title">
        Agent recommendation{" "}
        <span className={`chip ${agent.source.startsWith("ai:") ? "chip-ok" : ""}`}>{agentSourceLabel(agent.source)}</span>
      </h2>
      <p className="agent-pick">
        <strong>{optionLabel}</strong>
        <span className="muted"> · {strategyLabel(agent.strategy)}</span>
      </p>
      <AgentLists reasons={agent.reasons} risks={agent.risks} checks={agent.checks} />
      <p className="note">
        The agent only recommends. The controller approves it or chooses another option (an override) below.
      </p>
    </section>
  );
}

/** Recent agent runs (all users), newest first. */
export function AgentRunsList({ onOpen, refreshKey }: { onOpen: (id: string) => void; refreshKey?: unknown }) {
  const [runs, setRuns] = useState<AgentRunSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api
      .agentRuns()
      .then(setRuns)
      .catch((e: unknown) => setError(errorText(e, "Could not load the agent runs.")));
  }, [refreshKey]);
  return (
    <section aria-labelledby="runs-title" className="agent-runs">
      <h2 id="runs-title">Recent agent runs</h2>
      {error && <p className="error">{error}</p>}
      {runs && runs.length === 0 && <p className="muted">None yet. Use “Ask the agent” on a flight to start one.</p>}
      {runs && runs.length > 0 && (
        <ul>
          {runs.map((r) => (
            <li key={r.id}>
              <button type="button" className="link" onClick={() => onOpen(r.id)}>
                {flightLabel(r.flight_id)}
              </button>{" "}
              <span className={`chip ${STATUS_CHIP[r.status]}`}>{STATUS_LABEL[r.status]}</span>
              <span className="muted small">
                {" "}
                {r.source ? `${agentSourceLabel(r.source)} · ` : ""}
                {r.created_by}, {utc(r.created_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
