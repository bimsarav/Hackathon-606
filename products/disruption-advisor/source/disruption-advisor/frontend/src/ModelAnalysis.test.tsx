import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ModelCard } from "./api";
import { ModelAnalysis } from "./ModelAnalysis";

const metric = { observed_rate: 0.1, auc: 0.76, brier: 0.075, climatology_brier: 0.08, baseline_auc: 0.68, baseline_brier: 0.078 };
const card = {
  model: "LightGBM", trained_at: "2026-11-21T09:00:00Z", thresholds_minutes: [15, 60], features: ["origin"], assumptions: [],
  evaluation: {
    train: "a", test: "b", metrics_by_threshold: {}, connection_backtest: [],
    reliability_60: [{ from: 0.1, to: 0.2, flights: 1495, predicted: 0.142, observed: 0.122 }],
    arrival_model_metrics: { "60": { observed_rate: 0.088, auc: 0.7621, brier: 0.0794, climatology_brier: 0.0802 } },
    classification: {
      departure_60: {
        operating_points: [{ label: "Departure 60+ min late, flagged at 30% or more", cutoff: 0.3, true_positive: 100, false_positive: 300,
          false_negative: 200, true_negative: 5000, precision: 0.25, recall: 0.33, f1: 0.28, accuracy: 0.9, specificity: 0.94, flagged_share: 0.07 }],
        sweep: [{ cutoff: 0.05, precision: 0.1, recall: 1, f1: 0.18, flagged_share: 1 }],
        top_10_percent: { share: 0.1, flights: 595, late_rate: 0.284, overall_rate: 0.0878, lift: 3.23 },
      },
    },
    rolling_monthly: [{ month: "2026-07", train_flights: 30977, test_flights: 6993, "15": metric, "60": metric }],
  },
} as unknown as ModelCard;

const docs = {
  delay_selection: [
    { type: "title", text: "Model Selection" },
    { type: "paragraph", text: "Protocol: **time-ordered**." },
    { type: "table", header: ["Model", "AUC 60"], rows: [["LightGBM, tuned", "0.703"], ["route x hour baseline", "0.702"]] },
  ],
  reward_selection: [{ type: "table", header: ["Model", "Log-loss"], rows: [["LightGBM, tuned", "0.6153"]] }],
};
const reward = {
  synthetic_training_data: true, warning: "Trained on SIMULATED redemption history.", assumed_behaviour: ["Families like meals."],
  trained_at: "2026-11-21T08:59:02Z", features: ["fare_family", "severity"], categories: {},
  history: { offers: 300000, passengers: 111503, train_offers: 238836, test_offers: 61164 },
  metrics_on_held_out_passengers: { auc: 0.702, brier: 0.2112, baseline_type_average: { auc: 0.6165, brier: 0.2292 },
    baseline_proxy_rules: { auc: 0.6656 }, observed_acceptance_rate: 0.6,
    by_reward_type: { MEAL: { offers: 18048, acceptance_rate: 0.6335, auc: 0.6754 } } },
};
const cascade = {
  formula: "next departure = max(STD, previous arrival + 40 min)", definition: "d", from: "2026-10-22", to: "2026-11-21",
  kpis: { pairs: 1656, mean_delta: 4.2, within_15: 1000, within_15_share: 0.6, within_30: 1300, within_30_share: 0.78, underestimates: 300, overestimates: 100 },
  histogram: [], excluded: [{}, {}, {}], excluded_rule: "actual knock-on of 360 min or more", rows_total: 1656, rows: [],
};

function stub() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    const body = url.includes("model-docs") ? docs : url.includes("reward-model") ? reward : url.includes("cascade") ? cascade
      : { loaded: true, counts: { flights: 2, passengers: 2 }, risk: { scored: 2, connections: 2, reason: null } };
    return new Response(JSON.stringify(body), { status: 200 });
  }));
}
afterEach(() => vi.unstubAllGlobals());

describe("model analysis sections", () => {
  it("shows calibration, cut-offs, monthly and arrival results from the model card", async () => {
    stub();
    render(<ModelAnalysis card={card} />);
    await userEvent.click(screen.getByRole("button", { name: /Calibration/ }));
    const cal = screen.getByRole("table", { name: "Calibration" });
    expect(within(cal).getByText("14.2%")).toBeInTheDocument();
    expect(within(cal).getByText("12.2%")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Alert cut-offs/ }));
    const points = screen.getByRole("table", { name: "Operating points departure_60" });
    expect(within(points).getByText("100")).toBeInTheDocument(); // true alarms
    expect(screen.getByText(/3\.2× more/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Month-by-month/ }));
    expect(within(screen.getByRole("table", { name: "Month by month" })).getByText("2026-07")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Arrival-delay model/ }));
    expect(within(screen.getByRole("table", { name: "Arrival model" })).getByText("0.762")).toBeInTheDocument();
  });

  it("shows the model comparison, the reward model, the cascade check and how test flights are scored", async () => {
    stub();
    render(<ModelAnalysis card={card} />);
    await userEvent.click(screen.getByRole("button", { name: /Model comparison and tuning/ }));
    expect(await screen.findByText("LightGBM, tuned")).toBeInTheDocument();
    expect(screen.getByText("time-ordered").tagName).toBe("STRONG");
    await userEvent.click(screen.getByRole("button", { name: /Reward preference model/ }));
    expect(await screen.findByText(/Trained on SIMULATED redemption history/)).toBeInTheDocument();
    expect(screen.getByText("Families like meals.")).toBeInTheDocument();
    expect(within(screen.getByRole("table", { name: "By reward type" })).getByText("MEAL")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Cascade check/ }));
    expect(await screen.findByText(/max\(STD, previous arrival \+ 40 min\)/)).toBeInTheDocument();
    expect(screen.getByText(/1,656|1656/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /How uploaded test flights are scored/ }));
    expect(screen.getByText(/scored, never trained on/)).toBeInTheDocument();
    expect(await screen.findByText(/2 scored with the saved model/)).toBeInTheDocument();
  });
});
