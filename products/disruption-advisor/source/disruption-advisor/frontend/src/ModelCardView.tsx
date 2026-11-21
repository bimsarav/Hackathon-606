import { useEffect, useState } from "react";
import {
  api,
  type CascadeCheck,
  type CrewFdp,
  type DocBlock,
  errorText,
  type Meta,
  type ModelCard,
  type ModelDocs,
  type ModelMetrics,
  type RewardModelCard,
  type TestDataStatus,
} from "./api";
import { CrewFdpPanel } from "./CrewFdpPanel";
import { num } from "./format";
import { Arrival, Blocks, CascadeSummary, Cutoffs, Monthly, RewardModel, TestDataScoring } from "./ModelAnalysis";
import { BarChart, CalibrationChart, HBarChart, LineChart } from "./Charts";

// ── tiny helpers ────────────────────────────────────────────────────────────

function pct(v: number | null | undefined) {
  return v == null ? "—" : `${(v * 100).toFixed(1)}%`;
}
function auc(v: number | null | undefined) {
  return v == null ? "—" : v.toFixed(3);
}
function deltaPP(value: number | null | undefined, baseline: number | null | undefined) {
  if (value == null || baseline == null) return null;
  return (value - baseline) * 100;
}

// ── accordion row ────────────────────────────────────────────────────────────

function Decision({ badge, title, summary, detail }: {
  badge: string; title: string; summary: string; detail: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="decision-row">
      <button
        type="button"
        className="decision-trigger"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="chip chip-decision">{badge}</span>
        <span className="decision-title">{title}</span>
        <span className="decision-summary muted">{summary}</span>
        <span className="decision-chevron" aria-hidden="true">{open ? "▲" : "▾"}</span>
      </button>
      {open && <p className="decision-detail small">{detail}</p>}
    </div>
  );
}

// ── collapsible section wrapper ───────────────────────────────────────────────

function Expandable({ label, children }: { label: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="expand-section">
      <button type="button" className="expand-trigger link" onClick={() => setOpen((v) => !v)}>
        {open ? "▾" : "▸"} {label}
      </button>
      {open && <div className="expand-body">{children}</div>}
    </section>
  );
}

// ── metrics row ──────────────────────────────────────────────────────────────

function MetricRow({ threshold, m }: { threshold: string; m: ModelMetrics }) {
  const delta = deltaPP(m.auc, m.baseline_auc);
  const cls = delta == null ? "" : delta > 0 ? "text-ok" : "text-bad";
  return (
    <tr>
      <th scope="row">+{threshold} min</th>
      <td className="num">{auc(m.auc)}</td>
      <td className={`num ${cls}`}>
        {delta == null ? "—" : `${delta > 0 ? "+" : ""}${delta.toFixed(1)} pp`}
      </td>
      <td className="num">{auc(m.baseline_auc)}</td>
      <td className="num">{pct(m.observed_rate)}</td>
      <td className="num">{m.brier.toFixed(3)}</td>
    </tr>
  );
}

// ── design decisions ──────────────────────────────────────────────────────────

const DECISIONS = [
  {
    badge: "Algorithm",
    title: "LightGBM gradient-boosted trees",
    summary: "Outperformed logistic regression and random forests on AUC-60.",
    detail:
      "Chosen for native handling of categorical features (origin, destination, aircraft type) without one-hot encoding, fast training on ~63K flights, and built-in TreeSHAP for per-flight explanations. Gradient boosting consistently beat both alternatives during development.",
  },
  {
    badge: "Architecture",
    title: "One classifier per delay threshold",
    summary: "Six separate models (+5 to +180 min), outputs made monotone.",
    detail:
      "Six binary classifiers are trained independently, then constrained to form a valid delay curve S(t) where P(≥5) ≥ P(≥15) ≥ … ≥ P(≥180). A single multi-output model produced narrower SHAP explanations; separate models let each threshold capture its own feature relationships.",
  },
  {
    badge: "Weighting",
    title: "Recency-weighted training (half-life 109 days)",
    summary: "Tracks seasonal shifts without a manual re-train schedule.",
    detail:
      "Recent flights carry exponentially more weight so the model follows seasonal changes in delay rates automatically. The half-life (109 days) was itself tuned on the time-ordered validation blocks; a flight loses half its weight every 109 days of age.",
  },
  {
    badge: "Calibration",
    title: "Raw LightGBM probabilities — no isotonic step",
    summary: "Isotonic calibration was tested and made reliability worse.",
    detail:
      "An isotonic regression calibration step was tested on a held-out month but degraded reliability: delay rates shift month-to-month, so a calibrator fit on one period distorts the next. With recency weighting active, LightGBM's leaf-based probabilities are already well-calibrated. Recorded in docs/testing/model-card.md (2026-11-21).",
  },
  {
    badge: "Validation",
    title: "Time-ordered splits — no random cross-validation",
    summary: "Train on history before cut-off; test on the last 28 days.",
    detail:
      "Random splits would leak future delay rates into training (a flight's route delay rate uses neighbouring flights), inflating AUC. The rolling monthly back-test adds fold-by-fold temporal stability checks on top of the single hold-out.",
  },
  {
    badge: "Tuning",
    title: "Hyperparameters tuned with Optuna (40 trials, time-ordered validation)",
    summary: "Validation score 0.012 → 0.054 over the old settings; final-test AUC-60 0.756 → 0.761.",
    detail:
      "Selection metric: mean Brier skill score over three 28-day validation blocks (never the final test). Tuned values: learning_rate 0.0391, num_leaves 11, min_data_in_leaf 60, feature_fraction 0.99, bagging 0.856, λ_L2 17.25, cat_smooth 14.7, 120 rounds, half-life 109 days. Production adds the month and route_freq features (AUC-60 0.770 on the final test). Full comparison in the 'Models compared' chart and docs/testing/model-selection.md.",
  },
];

// ── data for the hub ─────────────────────────────────────────────────────────

interface HubData {
  card: ModelCard | null;
  docs: ModelDocs | null;
  reward: RewardModelCard | null;
  cascade: CascadeCheck | null;
  crew: CrewFdp | null;
  meta: Meta | null;
  testData: TestDataStatus | null;
}

/** First table of a write-up whose header contains every given column, as {model: {column: number}}. */
function docTable(
  blocks: DocBlock[] | undefined, columns: string[], rowHint?: string,
): { model: string; values: Record<string, number | null> }[] {
  const t = blocks?.find((b) => b.type === "table" && columns.every((c) => b.header.includes(c))
    && (!rowHint || b.rows.some((r) => (r[0] ?? "").includes(rowHint))));
  if (!t || t.type !== "table") return [];
  return t.rows.map((r) => ({
    model: (r[0] ?? "").replace(/\*\*/g, ""),
    values: Object.fromEntries(columns.map((c) => {
      const v = Number.parseFloat(r[t.header.indexOf(c)] ?? "");
      return [c, Number.isFinite(v) ? v : null];
    })),
  }));
}

const f3 = (v: number) => v.toFixed(3);
const pc0 = (v: number) => `${Math.round(v * 100)}%`;
const pc1 = (v: number) => `${(v * 100).toFixed(1)}%`;

// ── overview boxes ───────────────────────────────────────────────────────────

type BoxKey = "delay" | "arrival" | "reward" | "cascade" | "crew" | "priority" | "rebooking" | "ai" | "testdata";

function Box({ kind, title, stats, note, onOpen }: {
  kind: string; title: string; stats: { label: string; value: string }[]; note: string; onOpen: () => void;
}) {
  return (
    <button type="button" className="model-box" onClick={onOpen} aria-label={`${title}: open details`}>
      <span className="eyebrow">{kind}</span>
      <span className="model-box-title">{title}</span>
      <span className="model-box-stats">
        {stats.map((s) => (
          <span key={s.label} className="model-box-stat">
            <span className="model-box-value">{s.value}</span>
            <span className="model-box-label">{s.label}</span>
          </span>
        ))}
      </span>
      <span className="model-box-note small muted">{note}</span>
      <span className="model-box-open small">Open details →</span>
    </button>
  );
}

function Overview({ data, open }: { data: HubData; open: (k: BoxKey) => void }) {
  const ev = data.card?.evaluation;
  const m60 = ev?.metrics_by_threshold["60"];
  const arr60 = ev?.arrival_model_metrics?.["60"];
  const rm = data.reward?.metrics_on_held_out_passengers;
  const k = data.cascade?.kpis;
  const crew = data.crew?.summary;
  const w = data.meta?.default_weights;
  return (
    <>
      <header className="result-head">
        <p className="eyebrow">Evaluator view</p>
        <h1>Model overview</h1>
        <p className="muted">
          Every model, rule and AI component behind the recommendations. Each box shows the headline figures; open one
          for its evaluation, tuning and results as charts and tables.
        </p>
      </header>

      <h2 className="model-group">Prediction models</h2>
      <div className="model-grid">
        <Box kind="Prediction model · LightGBM" title="Delay risk (departure)" onOpen={() => open("delay")}
          stats={[
            { label: "AUC at +60 min", value: m60?.auc != null ? f3(m60.auc) : "—" },
            { label: "baseline", value: m60?.baseline_auc != null ? f3(m60.baseline_auc) : "—" },
            { label: "flights scored", value: data.card?.production ? num(data.card.production.scored_flights) : "—" },
          ]}
          note="Chance of each delay (5 to 180 min) for every flight in the next 7 days, with reasons." />
        <Box kind="Prediction model · LightGBM" title="Arrival delay & missed connections" onOpen={() => open("arrival")}
          stats={[
            { label: "arrival AUC +60", value: arr60 ? f3(arr60.auc) : "—" },
            { label: "connections scored", value: data.card?.connections ? num(data.card.connections.pairs) : "—" },
            { label: "slack buckets checked", value: ev ? String(ev.connection_backtest.length) : "—" },
          ]}
          note="Inbound arrival delay combined with the onward departure: each connecting passenger's risk." />
        <Box kind="Prediction model · LightGBM · synthetic data" title="Reward preference" onOpen={() => open("reward")}
          stats={[
            { label: "AUC (held-out)", value: rm ? f3(rm.auc) : "—" },
            { label: "baseline", value: rm ? f3(rm.baseline_type_average.auc) : "—" },
            { label: "simulated offers", value: data.reward ? num(data.reward.history.offers) : "—" },
          ]}
          note="Chance a passenger accepts a reward type and amount; trained on simulated history." />
      </div>

      <h2 className="model-group">Rules, optimiser and AI</h2>
      <div className="model-grid">
        <Box kind="Rule · checked against history" title="Cascade (knock-on) formula" onOpen={() => open("cascade")}
          stats={[
            { label: "aircraft pairs", value: k ? num(k.pairs) : "—" },
            { label: "within ±15 min", value: k?.within_15_share != null ? pc0(k.within_15_share) : "—" },
            { label: "mean error", value: k?.mean_delta != null ? `${k.mean_delta} min` : "—" },
          ]}
          note="Next departure = max(scheduled, previous arrival + 40 min), against last month's real departures." />
        <Box kind="Rule · crew roster" title="Crew duty time (FDP)" onOpen={() => open("crew")}
          stats={crew ? [
            { label: "duties analysed", value: num(crew.duties) },
            { label: "median headroom", value: `${num(crew.headroom_median)} min` },
            { label: "under 60 min left", value: `${crew.pct_under_60_left}%` },
          ] : [{ label: "crew roster", value: "not loaded" }]}
          note="Flags recovery options that would take a crew past its maximum flight duty period (alert only)." />
        <Box kind="Rules" title="Passenger priority" onOpen={() => open("priority")}
          stats={[
            { label: "strict tiers", value: "3" },
            { label: "weights inside a tier", value: w ? String(Object.keys(w).length) : "6" },
            { label: "non-revenue", value: "last" },
          ]}
          note="Care and urgency first; commercial value only orders passengers inside a tier." />
        <Box kind="Optimiser · OR-Tools CP-SAT" title="Seat-limited rebooking" onOpen={() => open("rebooking")}
          stats={[
            { label: "plan quality", value: "optimal" },
            { label: "147 pax / 60 seats", value: "< 1 s" },
            { label: "time limit", value: "5 s" },
          ]}
          note="Assigns passengers to alternative seats by priority, keeping families and groups together." />
        <Box kind={`Generative AI · ${data.meta?.ai_model ?? "Claude"}`} title="Explanations & agent" onOpen={() => open("ai")}
          stats={[
            { label: "status", value: data.meta ? (data.meta.ai_enabled ? "on" : "off (templates)") : "—" },
            { label: "agent tool calls", value: "≤ 12" },
            { label: "decides", value: "never" },
          ]}
          note="Words the engine's numbers and drafts messages; the agent recommends, a person approves." />
      </div>

      <h2 className="model-group">Evaluator data</h2>
      <div className="model-grid">
        <Box kind="Scoring, no training" title="Uploaded test flights" onOpen={() => open("testdata")}
          stats={data.testData?.loaded ? [
            { label: "flights loaded", value: String(data.testData.counts?.flights ?? 0) },
            { label: "scored", value: String(data.testData.risk?.scored ?? 0) },
          ] : [{ label: "loaded now", value: "none" }]}
          note="How flights from the Test data page are scored with the saved models." />
      </div>
    </>
  );
}

// ── detail pages ─────────────────────────────────────────────────────────────

function DelayDetail({ card, docs }: { card: ModelCard; docs: ModelDocs | null }) {
  const ev = card.evaluation;
  const m60 = ev.metrics_by_threshold["60"] as ModelMetrics | undefined;
  const delta60 = m60 ? deltaPP(m60.auc, m60.baseline_auc) : null;
  const ths = card.thresholds_minutes.filter((t) => ev.metrics_by_threshold[String(t)]);
  const sweep = ev.classification?.departure_60?.sweep ?? [];
  const compared = docTable(docs?.delay_selection, ["Score", "AUC 60"]);
  return (
    <>
      <header className="result-head">
        <p className="eyebrow">Prediction model · LightGBM</p>
        <h1>Delay risk (departure)</h1>
        <p className="muted">
          {card.model} · trained {card.trained_at.slice(0, 10)}
          {card.versions?.lightgbm && <> · LightGBM {card.versions.lightgbm}</>}
        </p>
        {card.target && <p className="small muted">Target: {card.target}</p>}
      </header>
      <section className="kpis" aria-label="Key numbers">
        <div className="kpi"><span className="kpi-label">AUC at +60 min</span><span className="kpi-value">{m60 ? auc(m60.auc) : "—"}</span><span className="kpi-sub">test weeks the model never saw</span></div>
        <div className="kpi"><span className="kpi-label">vs baseline</span><span className={`kpi-value ${delta60 != null && delta60 > 0 ? "text-ok" : ""}`}>{delta60 != null ? `${delta60 > 0 ? "+" : ""}${delta60.toFixed(1)} pp` : "—"}</span><span className="kpi-sub">route × hour historical rate</span></div>
        <div className="kpi"><span className="kpi-label">Brier at +60</span><span className="kpi-value">{m60 ? m60.brier.toFixed(3) : "—"}</span><span className="kpi-sub">plain average {m60 ? m60.climatology_brier.toFixed(3) : "—"}</span></div>
        {card.production && <div className="kpi"><span className="kpi-label">Flights scored</span><span className="kpi-value">{num(card.production.scored_flights)}</span><span className="kpi-sub">next 7 days</span></div>}
      </section>
      <p className="small muted">Train: {ev.train} · Test: {ev.test}.</p>

      <div className="chart-grid">
        <BarChart title="Ranking quality (AUC) by delay threshold" categories={ths.map((t) => `+${t} min`)} min={0.5} max={1}
          series={[
            { name: "Model", values: ths.map((t) => ev.metrics_by_threshold[String(t)]?.auc ?? null) },
            { name: "Route × hour baseline", values: ths.map((t) => ev.metrics_by_threshold[String(t)]?.baseline_auc ?? null) },
          ]} format={f3} caption="0.5 = chance, 1 = perfect ranking." />
        {ev.reliability_60 && ev.reliability_60.length > 0 && (
          <CalibrationChart title="Calibration: delay of 60+ minutes" bins={ev.reliability_60} />
        )}
        {ev.rolling_monthly && ev.rolling_monthly.length > 0 && (
          <LineChart title="Month by month: AUC at +60 min" categories={ev.rolling_monthly.map((f) => f.month)}
            series={[
              { name: "Model", values: ev.rolling_monthly.map((f) => (f["60"] as ModelMetrics | undefined)?.auc ?? null) },
              { name: "Route × hour baseline", values: ev.rolling_monthly.map((f) => (f["60"] as ModelMetrics | undefined)?.baseline_auc ?? null) },
            ]} format={f3} min={0.5} max={0.85} caption="Each month predicted by a model trained only on the months before it." />
        )}
        {sweep.length > 0 && (
          <LineChart title="Alert cut-off trade-off (60+ min)" categories={sweep.map((s) => pc0(s.cutoff))} min={0} max={1} xLabel="flag a flight when its chance reaches"
            series={[
              { name: "Precision (flagged that were late)", values: sweep.map((s) => s.precision) },
              { name: "Recall (late that were flagged)", values: sweep.map((s) => s.recall) },
            ]} format={pc0} />
        )}
        {compared.length > 0 && (
          <HBarChart title="Models compared on validation (Brier skill score)"
            items={compared.map((c) => ({ label: c.model, value: c.values.Score ?? null }))} format={(v) => v.toFixed(3)}
            highlight={(l) => l === "LightGBM, tuned"}
            caption="Higher is better; below 0 is worse than the plain average. Mean of three time-ordered blocks. LightGBM, tuned is in production." />
        )}
      </div>

      <section aria-labelledby="perf-title">
        <h2 id="perf-title">Performance by threshold</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th scope="col">Threshold</th><th scope="col" className="num">AUC</th><th scope="col" className="num">Δ vs baseline</th><th scope="col" className="num">Baseline AUC</th><th scope="col" className="num">Observed rate</th><th scope="col" className="num">Brier</th></tr></thead>
            <tbody>
              {card.thresholds_minutes.map((t) => {
                const m = ev.metrics_by_threshold[String(t)] as ModelMetrics | undefined;
                return m ? <MetricRow key={t} threshold={String(t)} m={m} /> : null;
              })}
            </tbody>
          </table>
        </div>
      </section>
      {ev.classification && <Expandable label="Alert cut-offs: true and false alarms (tables)"><Cutoffs all={ev.classification} /></Expandable>}
      {ev.rolling_monthly && <Expandable label="Month-by-month results (table)"><Monthly folds={ev.rolling_monthly} /></Expandable>}
      <Expandable label="Model comparison and tuning (write-up)">
        {docs ? <Blocks blocks={docs.delay_selection} /> : <p className="status">Loading…</p>}
      </Expandable>
      <section aria-labelledby="decisions-title" style={{ margin: "1.5rem 0" }}>
        <h2 id="decisions-title">Design decisions</h2>
        <div className="decisions-list">{DECISIONS.map((d) => <Decision key={d.badge} {...d} />)}</div>
      </section>
      <Expandable label={`Features used (${card.features.length})`}>
        <ul className="feature-list">{card.features.map((f) => <li key={f} className="mono small">{f}</li>)}</ul>
      </Expandable>
      <Expandable label="Assumptions & limitations">
        <ul className="small">{card.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul>
      </Expandable>
    </>
  );
}

function ArrivalDetail({ card }: { card: ModelCard }) {
  const ev = card.evaluation;
  const arr = ev.arrival_model_metrics ?? {};
  const bt = ev.connection_backtest;
  return (
    <>
      <header className="result-head">
        <p className="eyebrow">Prediction model · LightGBM</p>
        <h1>Arrival delay & missed connections</h1>
        <p className="muted">
          A second LightGBM curve predicts how late the inbound flight lands. A passenger misses the connection when the
          inbound arrival delay minus the onward departure delay exceeds the slack (connection time − minimum connection
          time); the two delays are taken as independent.
        </p>
      </header>
      <section className="kpis" aria-label="Key numbers">
        {Object.entries(arr).map(([t, m]) => (
          <div className="kpi" key={t}><span className="kpi-label">Arrival AUC at +{t} min</span><span className="kpi-value">{f3(m.auc)}</span><span className="kpi-sub">Brier {f3(m.brier)} vs {f3(m.climatology_brier)}</span></div>
        ))}
        {card.connections && <div className="kpi"><span className="kpi-label">Connections scored</span><span className="kpi-value">{num(card.connections.pairs)}</span><span className="kpi-sub">default MCT {card.connections.default_mct_minutes} min</span></div>}
      </section>
      <div className="chart-grid">
        {bt.length > 0 && (
          <BarChart title="Missed connections: predicted vs what happened, by slack" categories={bt.map((r) => r.slack)}
            series={[{ name: "Predicted", values: bt.map((r) => r.predicted) }, { name: "Happened", values: bt.map((r) => r.observed) }]}
            format={pc1} caption="Historical connections in the test weeks; slack = connection time − MCT." />
        )}
        {Object.keys(arr).length > 0 && (
          <BarChart title="Arrival model: Brier against the plain average" categories={Object.keys(arr).map((t) => `+${t} min`)}
            series={[{ name: "Model", values: Object.values(arr).map((m) => m.brier) }, { name: "Plain average", values: Object.values(arr).map((m) => m.climatology_brier) }]}
            format={f3} caption="Lower is better." />
        )}
      </div>
      {bt.length > 0 && (
        <section aria-labelledby="bt-title">
          <h2 id="bt-title">Missed-connection backtest</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th scope="col">Slack</th><th scope="col" className="num">Pairs</th><th scope="col" className="num">Predicted</th><th scope="col" className="num">Happened</th></tr></thead>
              <tbody>{bt.map((r) => <tr key={r.slack}><th scope="row">{r.slack}</th><td className="num">{num(r.pairs)}</td><td className="num">{pct(r.predicted)}</td><td className="num">{pct(r.observed)}</td></tr>)}</tbody>
            </table>
          </div>
        </section>
      )}
      {Object.keys(arr).length > 0 && <Arrival metrics={arr} />}
    </>
  );
}

function RewardDetail({ reward, docs }: { reward: RewardModelCard | null; docs: ModelDocs | null }) {
  const m = reward?.metrics_on_held_out_passengers;
  const types = m ? Object.entries(m.by_reward_type) : [];
  const final = docTable(docs?.reward_selection, ["AUC", "Brier", "Log-loss"], "Oracle").filter((r) => r.values.AUC != null);
  return (
    <>
      <header className="result-head">
        <p className="eyebrow">Prediction model · LightGBM · synthetic data</p>
        <h1>Reward preference</h1>
      </header>
      {m && (
        <>
          <section className="kpis" aria-label="Key numbers">
            <div className="kpi"><span className="kpi-label">AUC (held-out passengers)</span><span className="kpi-value">{f3(m.auc)}</span><span className="kpi-sub">baseline {f3(m.baseline_type_average.auc)} · rules {f3(m.baseline_proxy_rules.auc)}</span></div>
            <div className="kpi"><span className="kpi-label">Brier</span><span className="kpi-value">{f3(m.brier)}</span><span className="kpi-sub">baseline {f3(m.baseline_type_average.brier)}</span></div>
            <div className="kpi"><span className="kpi-label">Acceptance in test</span><span className="kpi-value">{pc0(m.observed_acceptance_rate)}</span><span className="kpi-sub">{reward ? `${num(reward.history.test_offers)} offers` : ""}</span></div>
          </section>
          <div className="chart-grid">
            <BarChart title="Ranking quality (AUC) by reward type" categories={types.map(([t]) => t)} min={0.5} max={1}
              series={[{ name: "AUC", values: types.map(([, r]) => r.auc) }]} format={f3} />
            <BarChart title="Acceptance rate by reward type (simulated)" categories={types.map(([t]) => t)} min={0} max={1}
              series={[{ name: "Acceptance", values: types.map(([, r]) => r.acceptance_rate) }]} format={pc0} />
            {m.reliability && m.reliability.length > 0 && <CalibrationChart title="Calibration: predicted acceptance" bins={m.reliability} />}
            {final.length > 0 && (
              <HBarChart title="Models compared on the final test (AUC)"
                items={final.map((r) => ({ label: r.model, value: r.values.AUC ?? null }))} format={f3}
                highlight={(l) => l.includes("adopted")}
                caption="The oracle is the best any model could score on this simulated data." />
            )}
          </div>
        </>
      )}
      <RewardModel docs={docs} />
    </>
  );
}

function CascadeDetail({ cascade }: { cascade: CascadeCheck | null }) {
  return (
    <>
      <header className="result-head">
        <p className="eyebrow">Rule · checked against history</p>
        <h1>Cascade (knock-on) formula</h1>
      </header>
      {cascade && cascade.histogram.length > 0 && (
        <div className="chart-grid">
          <BarChart title="Error of the formula (actual − formula knock-on, minutes)" categories={cascade.histogram.map((h) => h.label)}
            series={[{ name: "Aircraft pairs", values: cascade.histogram.map((h) => h.count) }]} format={(v) => num(Math.round(v))}
            caption="Positive: the formula under-estimated the knock-on delay." />
        </div>
      )}
      <CascadeSummary />
    </>
  );
}

function CrewDetail({ crew }: { crew: CrewFdp | null }) {
  return (
    <>
      <header className="result-head">
        <p className="eyebrow">Rule · crew roster</p>
        <h1>Crew duty time (FDP)</h1>
        <p className="muted">
          Each recovery option is checked against the tightest crew member's remaining flight duty period. An option that
          would pass the maximum is flagged as a breach, under {crew?.rules.tight_below_minutes ?? 30} minutes left as tight.
          Alert only: no crew recovery is planned.
        </p>
      </header>
      {crew && (
        <div className="chart-grid">
          {crew.extra_delay.length > 0 && (
            <LineChart title="Duties that would pass the maximum FDP with extra delay" categories={crew.extra_delay.map((r) => `+${r.extra_minutes}`)}
              series={[{ name: "Share over the maximum", values: crew.extra_delay.map((r) => r.pct_over_max / 100) }]} min={0} format={pc0} xLabel="extra delay (minutes)" />
          )}
          {crew.bands.length > 0 && (
            <BarChart title="Headroom left after the planned duty" categories={crew.bands.map((b) => b.band)}
              series={[{ name: "Duties", values: crew.bands.map((b) => b.duties) }]} format={(v) => num(Math.round(v))} />
          )}
        </div>
      )}
      <CrewFdpPanel />
      {!crew && <p className="muted">The crew roster is not loaded on this server, so the check has no data.</p>}
    </>
  );
}

function PriorityDetail({ meta }: { meta: Meta | null }) {
  const keys = meta ? (Object.keys(meta.default_weights) as (keyof Meta["default_weights"])[]) : [];
  return (
    <>
      <header className="result-head">
        <p className="eyebrow">Rules</p>
        <h1>Passenger priority</h1>
        <p className="muted">Strict tiers first, then a weighted score inside each tier, so commercial value can never move someone across a tier.</p>
      </header>
      <div className="table-wrap">
        <table>
          <thead><tr><th scope="col">Tier</th><th scope="col">Who</th></tr></thead>
          <tbody>
            <tr><th scope="row">1 · Mandated care</th><td>Special assistance (WCHR, WCHS, WCHC, BLND, DEAF, MEDA, PREG) and bookings travelling with an infant.</td></tr>
            <tr><th scope="row">2 · Urgency</th><td>An onward connection, or a multi-sector journey.</td></tr>
            <tr><th scope="row">3 · Everyone else</th><td>Ordered by the weighted score below.</td></tr>
            <tr><th scope="row">Last</th><td>Non-revenue passengers, after all revenue passengers.</td></tr>
          </tbody>
        </table>
      </div>
      {meta && (
        <div className="chart-grid">
          <BarChart title="Default weights inside a tier (what-if sliders change them)" categories={keys.map((k) => meta.weight_labels[k])}
            series={[{ name: "Weight", values: keys.map((k) => meta.default_weights[k]) }]} format={(v) => String(Math.round(v))} />
        </div>
      )}
      <p className="small muted">
        Loyalty: Basic &lt; Silver &lt; Gold &lt; Platinum (recovery priority Lowest to High); a family booking travels on the head
        of family's tier. Loyalty tiers, fare families and special-service codes are partly synthetic in this data.
      </p>
    </>
  );
}

function RebookingDetail() {
  return (
    <>
      <header className="result-head">
        <p className="eyebrow">Optimiser · OR-Tools CP-SAT</p>
        <h1>Seat-limited rebooking</h1>
        <p className="muted">When alternatives have fewer seats than passengers, passengers are assigned by priority as a 0/1 integer programme (ADR 0006).</p>
      </header>
      <div className="table-wrap">
        <table>
          <tbody>
            <tr><th scope="row">Variables</th><td>One per (booking group, alternative flight); at most one flight per group.</td></tr>
            <tr><th scope="row">Constraints</th><td>Seats per flight no more than its free seats; families and groups stay together where any block fits, otherwise the split is reported.</td></tr>
            <tr><th scope="row">Objective</th><td>Widely separated tier values (100,000 / 5,000 / 200) plus the 0–100 priority score, minus lateness and lost-onward-connection penalties.</td></tr>
            <tr><th scope="row">Result</th><td>Proven optimal plans in under a second on real cases (147 passengers for 60 seats); 5-second time limit.</td></tr>
            <tr><th scope="row">Alternatives rejected</th><td>Greedy fill by rank (strands families, wastes seats); PuLP/HiGHS (slower on integer problems); a learned policy (no training data, no guarantees).</td></tr>
          </tbody>
        </table>
      </div>
    </>
  );
}

function AiDetail({ meta }: { meta: Meta | null }) {
  return (
    <>
      <header className="result-head">
        <p className="eyebrow">Generative AI · {meta?.ai_model ?? "Claude"}</p>
        <h1>Explanations & agent</h1>
        <p className="muted">
          {meta ? (meta.ai_enabled ? `On: texts are written by ${meta.ai_model}.` : "Off on this server: template texts and the rule-based planner answer.") : ""}{" "}
          The numbers always come from the recovery engine; the model only words them and never decides.
        </p>
      </header>
      <div className="table-wrap">
        <table>
          <tbody>
            <tr><th scope="row">Explanations</th><td>"Why?" text for each recommendation and personalised passenger messages, grounded in the engine's figures.</td></tr>
            <tr><th scope="row">Agent</th><td>Tool-using loop (find flights, status, rotation, assess delay, compare strategies, passenger impact, watchlist) that recommends one option for a person to approve.</td></tr>
            <tr><th scope="row">Limits</th><td>At most 12 tool calls and 120 seconds per run; one run at a time per user; a final answer is accepted only for an option the engine produced.</td></tr>
            <tr><th scope="row">Fallback</th><td>Refusal, error, time-out or no key: the deterministic planner finishes the run, and its steps stay in the trace.</td></tr>
            <tr><th scope="row">Evidence</th><td>10 automated tests with a scripted client (loop, privacy of passenger data, invented options refused, fallback); live check on G9519: 7 tool calls in 37 s, grounded recommendation.</td></tr>
            <tr><th scope="row">Known limits</th><td>Wording varies between runs (the option list and its numbers do not); it inherits the engine's assumptions (assumed costs, synthetic loyalty data).</td></tr>
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── main view ─────────────────────────────────────────────────────────────────

const TITLES: Record<BoxKey, string> = {
  delay: "Delay risk", arrival: "Arrival & missed connections", reward: "Reward preference", cascade: "Cascade formula",
  crew: "Crew duty time", priority: "Passenger priority", rebooking: "Rebooking optimiser", ai: "Explanations & agent",
  testdata: "Uploaded test flights",
};

export function ModelCardView() {
  const [data, setData] = useState<HubData>({ card: null, docs: null, reward: null, cascade: null, crew: null, meta: null, testData: null });
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<BoxKey | null>(null);

  useEffect(() => {
    const put = <K extends keyof HubData>(key: K) => (value: HubData[K]) => setData((d) => ({ ...d, [key]: value }));
    api.modelCard().then(put("card")).catch((e: unknown) => setError(errorText(e, "Could not load model information.")));
    api.modelDocs().then(put("docs")).catch(() => {});
    api.rewardModel().then(put("reward")).catch(() => {});
    api.cascade().then(put("cascade")).catch(() => {});
    api.crewFdp().then(put("crew")).catch(() => {});
    api.meta().then(put("meta")).catch(() => {});
    api.testData().then(put("testData")).catch(() => {});
  }, []);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!data.card) return <p className="status">Loading…</p>;

  return (
    <article className="result model-hub">
      {open ? (
        <>
          <nav className="model-back" aria-label="Model card">
            <button type="button" className="link" onClick={() => setOpen(null)}>← All models</button>
            <span className="muted small"> / {TITLES[open]}</span>
          </nav>
          {open === "delay" && <DelayDetail card={data.card} docs={data.docs} />}
          {open === "arrival" && <ArrivalDetail card={data.card} />}
          {open === "reward" && <RewardDetail reward={data.reward} docs={data.docs} />}
          {open === "cascade" && <CascadeDetail cascade={data.cascade} />}
          {open === "crew" && <CrewDetail crew={data.crew} />}
          {open === "priority" && <PriorityDetail meta={data.meta} />}
          {open === "rebooking" && <RebookingDetail />}
          {open === "ai" && <AiDetail meta={data.meta} />}
          {open === "testdata" && (
            <>
              <header className="result-head"><p className="eyebrow">Scoring, no training</p><h1>Uploaded test flights</h1></header>
              <TestDataScoring />
            </>
          )}
        </>
      ) : (
        <Overview data={data} open={setOpen} />
      )}
    </article>
  );
}
