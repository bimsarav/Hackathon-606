import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ModelCardView } from "./ModelCardView";

const metric = (auc: number, base: number) => ({ observed_rate: 0.1, auc, brier: 0.075, climatology_brier: 0.08, baseline_auc: base, baseline_brier: 0.078 });
const card = {
  model: "LightGBM binary classifier per threshold", trained_at: "2026-11-21T09:00:00Z", thresholds_minutes: [15, 60],
  features: ["origin", "month"], assumptions: ["Only information known 7 days ahead is used."], versions: { lightgbm: "4.7.0" },
  production: { train: "x", scored_flights: 2623, bands_on_p60: { high: 0.3, medium: 0.15 } },
  connections: { pairs: 88434, default_mct_minutes: 50 },
  evaluation: {
    train: "2026-01-01 .. 2026-10-21", test: "2026-10-21 .. 2026-11-18",
    metrics_by_threshold: { "15": metric(0.801, 0.741), "60": metric(0.77, 0.677) },
    connection_backtest: [{ slack: "0-30 min", pairs: 1200, predicted: 0.21, observed: 0.19 }],
    reliability_60: [{ from: 0.1, to: 0.2, flights: 1495, predicted: 0.142, observed: 0.122 }],
    arrival_model_metrics: { "60": { observed_rate: 0.088, auc: 0.7621, brier: 0.0794, climatology_brier: 0.0802 } },
    classification: { departure_60: {
      operating_points: [{ label: "flag at 30%", cutoff: 0.3, true_positive: 100, false_positive: 300, false_negative: 200, true_negative: 5000,
        precision: 0.25, recall: 0.33, f1: 0.28, accuracy: 0.9, specificity: 0.94, flagged_share: 0.07 }],
      sweep: [{ cutoff: 0.1, precision: 0.15, recall: 0.9, f1: 0.26, flagged_share: 0.5 }, { cutoff: 0.3, precision: 0.25, recall: 0.33, f1: 0.28, flagged_share: 0.07 }],
      top_10_percent: { share: 0.1, flights: 595, late_rate: 0.284, overall_rate: 0.0878, lift: 3.23 } } },
    rolling_monthly: [
      { month: "2026-07", train_flights: 30977, test_flights: 6993, "15": metric(0.727, 0.639), "60": metric(0.7, 0.537) },
      { month: "2026-08", train_flights: 37970, test_flights: 7517, "15": metric(0.731, 0.688), "60": metric(0.744, 0.702) },
    ],
  },
};
const docs = {
  delay_selection: [
    { type: "heading", text: "Validation results" },
    { type: "table", header: ["Model", "Score", "AUC 15", "Brier 15", "AUC 60", "Brier 60"],
      rows: [["LightGBM, tuned", "0.054", "0.736", "0.2057", "0.703", "0.0944"], ["prior (dummy)", "-0.032", "0.500", "0.2463", "0.500", "0.0982"]] },
  ],
  reward_selection: [
    { type: "table", header: ["Model", "AUC", "Brier", "Log-loss"],
      rows: [["type average (baseline)", "0.6128", "0.2315", "0.6552"], ["proxy rules (first version)", "0.6666", "n/a", "n/a"], ["**LightGBM, tuned (adopted)**", "0.7023", "0.2132", "0.6147"], ["Oracle: the best any model could do", "0.7386", "0.2019", "0.5890"]] },
  ],
};
const reward = {
  synthetic_training_data: true, warning: "Trained on SIMULATED redemption history.", assumed_behaviour: ["Families like meals."],
  trained_at: "2026-11-21T08:59:02Z", features: ["fare_family"], categories: {},
  history: { offers: 300000, passengers: 111503, train_offers: 238836, test_offers: 61164 },
  metrics_on_held_out_passengers: { auc: 0.702, brier: 0.2112, baseline_type_average: { auc: 0.6165, brier: 0.2292 }, baseline_proxy_rules: { auc: 0.6656 },
    observed_acceptance_rate: 0.6, by_reward_type: { MEAL: { offers: 18048, acceptance_rate: 0.6335, auc: 0.6754 }, LOUNGE: { offers: 18132, acceptance_rate: 0.465, auc: 0.677 } } },
};
const cascade = {
  formula: "next departure = max(STD, previous arrival + 40 min)", definition: "d", from: "2026-10-22", to: "2026-11-21",
  kpis: { pairs: 1656, mean_delta: 10, within_15: 1243, within_15_share: 0.7506, within_30: 1546, within_30_share: 0.93, underestimates: 412, overestimates: 1 },
  histogram: [{ label: "< -15", count: 1 }, { label: "0 to 15", count: 900 }], excluded: [], excluded_rule: "360+", rows_total: 1656, rows: [],
};
const meta = {
  user: { username: "judge", role: "EVALUATOR" }, now_utc: "2026-11-20T00:00:00", horizon_days: 7, ai_enabled: true, ai_model: "claude-opus-5-5",
  default_weights: { loyalty: 20, frequency: 15, fare_value: 20, ancillaries: 10, journey: 20, booking: 15 },
  weight_labels: { loyalty: "Loyalty tier", frequency: "Travel frequency", fare_value: "Fare value", ancillaries: "Ancillary purchases", journey: "Journey complexity", booking: "Family / group booking" },
  ingest: {},
};

function stub() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.includes("/crew/fdp")) return new Response(JSON.stringify({ title: "Not Found", status: 404 }), { status: 404 });
    const body = url.includes("model-docs") ? docs : url.includes("reward-model") ? reward : url.includes("/risk/model") ? card
      : url.includes("cascade") ? cascade : url.includes("/meta") ? meta : { loaded: false };
    return new Response(JSON.stringify(body), { status: 200 });
  }));
}
afterEach(() => vi.unstubAllGlobals());

describe("model card hub", () => {
  it("shows one box per model and rule with its headline figures", async () => {
    stub();
    render(<ModelCardView />);
    const delay = await screen.findByRole("button", { name: /Delay risk \(departure\): open details/ });
    expect(within(delay).getByText("0.770")).toBeInTheDocument();
    expect(within(delay).getByText("0.677")).toBeInTheDocument();
    expect(within(delay).getByText("2,623")).toBeInTheDocument();
    const names = ["Arrival delay & missed connections", "Reward preference", "Cascade (knock-on) formula", "Crew duty time (FDP)",
      "Passenger priority", "Seat-limited rebooking", "Explanations & agent", "Uploaded test flights"];
    for (const n of names) expect(screen.getByRole("button", { name: new RegExp(`^${n.replace(/[()]/g, "\\$&")}: open details`) })).toBeInTheDocument();
    expect(within(await screen.findByRole("button", { name: /Reward preference: open/ })).findByText("0.702")).toBeTruthy();
    expect(within(screen.getByRole("button", { name: /Crew duty time/ })).getByText("not loaded")).toBeInTheDocument();
    expect(await within(screen.getByRole("button", { name: /Cascade/ })).findByText("75%")).toBeInTheDocument();
  });

  it("opens the delay model with charts and tables, and goes back to the overview", async () => {
    stub();
    render(<ModelCardView />);
    await userEvent.click(await screen.findByRole("button", { name: /Delay risk \(departure\): open details/ }));
    expect(screen.getByRole("heading", { level: 1, name: "Delay risk (departure)" })).toBeInTheDocument();
    for (const chart of ["Ranking quality (AUC) by delay threshold", "Calibration: delay of 60+ minutes", "Month by month: AUC at +60 min",
      "Alert cut-off trade-off (60+ min)", "Models compared on validation (Brier skill score)"]) {
      expect(await screen.findByRole("img", { name: chart })).toBeInTheDocument();
    }
    const bars = screen.getByRole("img", { name: "Ranking quality (AUC) by delay threshold" });
    fireEvent.mouseEnter(bars.querySelector("path") as Element);
    expect(within(bars).getByText("Model: 0.801")).toBeInTheDocument(); // tooltip
    expect(screen.getByRole("heading", { name: "Performance by threshold" })).toBeInTheDocument();
    expect(screen.getByText(/half-life 109 days/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "← All models" }));
    expect(screen.getByRole("heading", { level: 1, name: "Model overview" })).toBeInTheDocument();
  });

  it("opens the reward model, the passenger priority rules and the AI component", async () => {
    stub();
    render(<ModelCardView />);
    await userEvent.click(await screen.findByRole("button", { name: /Reward preference: open/ }));
    expect(await screen.findByRole("img", { name: "Ranking quality (AUC) by reward type" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Models compared on the final test (AUC)" })).toBeInTheDocument();
    expect(await screen.findByText(/Trained on SIMULATED redemption history/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "← All models" }));
    await userEvent.click(screen.getByRole("button", { name: /Passenger priority: open/ }));
    expect(screen.getByText(/1 · Mandated care/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Default weights inside a tier/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "← All models" }));
    await userEvent.click(screen.getByRole("button", { name: /Explanations & agent: open/ }));
    expect(screen.getByText(/On: texts are written by claude-opus-5-5/)).toBeInTheDocument();
  });
});
