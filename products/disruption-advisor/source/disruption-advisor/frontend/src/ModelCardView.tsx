import { useEffect, useState } from "react";
import { api, type ModelCard, type ModelMetrics, errorText } from "./api";
import { CrewFdpPanel } from "./CrewFdpPanel";
import { num } from "./format";
import { ModelAnalysis } from "./ModelAnalysis";

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
    title: "Recency-weighted training (half-life 60 days)",
    summary: "Tracks seasonal shifts without a manual re-train schedule.",
    detail:
      "Recent flights carry exponentially more weight so the model follows seasonal changes in delay rates automatically. The 60-day half-life means the last two months contribute roughly as much as all older history combined.",
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
    title: "Hyperparameters tuned with Optuna (60 trials)",
    summary: "AUC-60 improved from 0.768 → 0.789 (+2.1 pp) over defaults.",
    detail:
      "Primary metric: AUC on the 60-min threshold. Best params: learning_rate 0.0137, num_leaves 93, min_data_in_leaf 184, feature_fraction 0.562, λ_L2 0.164, bagging 0.576/freq 4, 401 rounds.",
  },
];

// ── main view ─────────────────────────────────────────────────────────────────

export function ModelCardView() {
  const [card, setCard] = useState<ModelCard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.modelCard()
      .then(setCard)
      .catch((e: unknown) => setError(errorText(e, "Could not load model information.")));
  }, []);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!card) return <p className="status">Loading…</p>;

  const m60 = card.evaluation.metrics_by_threshold["60"] as ModelMetrics | undefined;
  const delta60 = m60 ? deltaPP(m60.auc, m60.baseline_auc) : null;
  const lgbVersion = card.versions?.lightgbm ?? null;

  return (
    <article className="result">

      {/* ── header ── */}
      <header className="result-head">
        <p className="eyebrow">Delay risk model</p>
        <h1>Model overview</h1>
        <p className="muted">
          LightGBM binary classifier · trained {card.trained_at.slice(0, 10)}
          {lgbVersion && <> · LightGBM {lgbVersion}</>}
          {card.production && <> · {num(card.production.scored_flights)} flights scored in production</>}
        </p>
        {card.target && <p className="small muted" style={{ marginTop: "0.25rem" }}>Target: {card.target}</p>}
      </header>

      {/* ── 3 key numbers ── */}
      <section className="kpis" aria-label="Key numbers" style={{ marginBottom: "2rem" }}>
        <div className="kpi">
          <span className="kpi-label">AUC at +60 min</span>
          <span className="kpi-value">{m60 ? auc(m60.auc) : "—"}</span>
          <span className="kpi-sub">main operational threshold</span>
        </div>
        <div className="kpi">
          <span className="kpi-label">vs baseline</span>
          <span className={`kpi-value ${delta60 != null && delta60 > 0 ? "text-ok" : ""}`}>
            {delta60 != null ? `${delta60 > 0 ? "+" : ""}${delta60.toFixed(1)} pp` : "—"}
          </span>
          <span className="kpi-sub">route × hour historical rate</span>
        </div>
        {card.production && (
          <div className="kpi">
            <span className="kpi-label">Risk bands (P60)</span>
            <span className="kpi-value">
              {Math.round(card.production.bands_on_p60.high * 100)}% / {Math.round(card.production.bands_on_p60.medium * 100)}%
            </span>
            <span className="kpi-sub">high / medium threshold</span>
          </div>
        )}
        <div className="kpi">
          <span className="kpi-label">Thresholds modelled</span>
          <span className="kpi-value">{card.thresholds_minutes.length}</span>
          <span className="kpi-sub">{card.thresholds_minutes.map(t => `+${t}`).join(", ")} min</span>
        </div>
      </section>

      {/* ── design decisions ── */}
      <section aria-labelledby="decisions-title" style={{ marginBottom: "2rem" }}>
        <h2 id="decisions-title">Design decisions</h2>
        <p className="small muted" style={{ marginBottom: "0.75rem" }}>
          Why this approach was chosen. Expand any row for the full reasoning.
        </p>
        <div className="decisions-list">
          {DECISIONS.map((d) => (
            <Decision key={d.badge} {...d} />
          ))}
        </div>
      </section>

      {/* ── performance detail ── */}
      <Expandable label="Performance by threshold">
        <p className="small muted" style={{ marginBottom: "0.75rem" }}>
          AUC: higher is better (0.5 = random). Brier: lower is better. Δ vs baseline in percentage points.
          Train: {card.evaluation.train} · Test: {card.evaluation.test}.
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Threshold</th>
                <th scope="col" className="num">AUC</th>
                <th scope="col" className="num">Δ vs baseline</th>
                <th scope="col" className="num">Baseline AUC</th>
                <th scope="col" className="num">Observed rate</th>
                <th scope="col" className="num">Brier</th>
              </tr>
            </thead>
            <tbody>
              {card.thresholds_minutes.map((t) => {
                const m = card.evaluation.metrics_by_threshold[String(t)] as ModelMetrics | undefined;
                return m ? <MetricRow key={t} threshold={String(t)} m={m} /> : null;
              })}
            </tbody>
          </table>
        </div>
      </Expandable>

      {/* ── connection backtest ── */}
      {card.evaluation.connection_backtest.length > 0 && (
        <Expandable label="Missed-connection backtest by slack bucket">
          <p className="small muted" style={{ marginBottom: "0.75rem" }}>
            Slack = connection time − MCT. Predicted vs observed on historical data.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Slack</th>
                  <th scope="col" className="num">Pairs</th>
                  <th scope="col" className="num">Predicted</th>
                  <th scope="col" className="num">Observed</th>
                </tr>
              </thead>
              <tbody>
                {card.evaluation.connection_backtest.map((r) => {
                  const diff = Math.abs(r.predicted - r.observed);
                  const cls = diff < 0.05 ? "text-ok" : diff < 0.10 ? "text-warn" : "text-bad";
                  return (
                    <tr key={r.slack}>
                      <th scope="row">{r.slack}</th>
                      <td className="num">{num(r.pairs)}</td>
                      <td className={`num ${cls}`}>{pct(r.predicted)}</td>
                      <td className="num">{pct(r.observed)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Expandable>
      )}

      {/* ── features ── */}
      <Expandable label={`Features used (${card.features.length})`}>
        <ul className="feature-list">
          {card.features.map((f) => (
            <li key={f} className="mono small">{f}</li>
          ))}
        </ul>
      </Expandable>

      {/* ── assumptions ── */}
      <Expandable label="Assumptions & limitations">
        <ul style={{ paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {card.assumptions.map((a, i) => (
            <li key={i} className="small">{a}</li>
          ))}
        </ul>
      </Expandable>

      <ModelAnalysis card={card} />
      <CrewFdpPanel />

    </article>
  );
}
