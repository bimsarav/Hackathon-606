import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type AgentRun, ApiError, type DelayResult, type Meta, type RecoveryOption, type Scenario } from "./api";
import { agentStartError, AgentRunView } from "./AgentRunView";
import { DelayView } from "./DelayView";
import { WatchlistView } from "./WatchlistView";

const weights = { loyalty: 20, frequency: 15, fare_value: 20, ancillaries: 10, journey: 20, booking: 15 };
const meta: Meta = {
  user: { username: "occ", role: "OCC" },
  now_utc: "2026-11-20T00:00:00",
  horizon_days: 7,
  ai_enabled: true,
  ai_model: "claude-opus-5-5",
  default_weights: weights,
  weight_labels: {
    loyalty: "Loyalty tier", frequency: "Travel frequency", fare_value: "Fare value",
    ancillaries: "Ancillary purchases", journey: "Journey complexity", booking: "Family / group booking",
  },
  ingest: {},
};
const flight = {
  flight_id: "G9519_202611210200", flight_number: "G9519", airline: "G9", tail: "A6-AOH", origin: "MCT",
  destination: "SHJ", std: "2026-11-21T02:00:00", sta: "2026-11-21T03:00:00", capacity: 174, booked_seats: 160,
  booked_pax: 162, aircraft_model: "A320-174", capacity_source: "inventory-exact",
};

const option = (o: Partial<RecoveryOption> & Pick<RecoveryOption, "key" | "label">): RecoveryOption => ({
  total_delay_minutes: 150, legs_delayed: 1, delayed_passengers: 162, misconnects: 10, connections_checked: 100,
  eu261_compensation_eur: 0, cost_aed: 50000, cost_breakdown: {}, legs: [], kind: "absorb", cancelled_flights: [],
  cancelled_passengers: 0, passengers_rebooked: 10, passengers_without_seat: 0, passenger_delay_minutes: 24000,
  picked_by: [], ...o,
});

const options: RecoveryOption[] = [
  option({ key: "swap:A6-ARI", label: "Swap: A6-ARI takes over G9520", kind: "swap", cost_aed: 40000, misconnects: 12,
    passengers_without_seat: 4, picked_by: ["lowest_cost"] }),
  option({ key: "cancel:G9521", label: "Cancel G9521/G9522 round trip", kind: "cancel", cost_aed: 60000, misconnects: 2,
    cancelled_passengers: 150, passenger_delay_minutes: 12000,
    cancelled_flights: [{ flight_id: "G9521_202611210900", flight_number: "G9521", origin: "SHJ", destination: "KHI",
      std: "2026-11-21T09:00:00", booked_pax: 150 }], picked_by: ["least_delay"] }),
  option({ key: "absorb", label: "Absorb the delay on A6-AOH", cost_aed: 90000, misconnects: 1,
    picked_by: ["protect_passengers"] }),
];

function delayScenario(result: Partial<DelayResult> = {}): Scenario {
  return {
    id: "s1", kind: "DELAY", flight_id: flight.flight_id, delay_minutes: 150, weights, created_by: "occ",
    created_at: "2026-11-20T10:00:00",
    result: {
      type: "DELAY", flight, delay_minutes: 150, recommended_key: "swap:A6-ARI", selected_key: "swap:A6-ARI",
      strategy: "lowest_cost",
      strategies: [
        { key: "lowest_cost", label: "Lowest cost", pick: "swap:A6-ARI" },
        { key: "protect_passengers", label: "Protect passengers", pick: "absorb" },
        { key: "least_delay", label: "Least delay", pick: "cancel:G9521" },
      ],
      explanation: { text: "Swap is cheaper.", source: "template" }, passengers: [], rebooking: null,
      misconnections: [], assumptions: [], options, ...result,
    },
  };
}

type Handler = (url: string, init?: RequestInit) => unknown;
function stubFetch(handler: Handler) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    const body = handler(url, init);
    if (body instanceof Response) return body;
    return new Response(JSON.stringify(body), { status: 200 });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

beforeEach(() => sessionStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe("strategy comparison", () => {
  it("shows the three strategies with their picks and switches the active one on the server", async () => {
    const switched = delayScenario({ strategy: "least_delay", recommended_key: "cancel:G9521", selected_key: "cancel:G9521" });
    const fetchFn = stubFetch((url) => (url.endsWith("/strategy") ? switched : []));
    const onUpdate = vi.fn();
    const scenario = delayScenario();
    render(<DelayView scenario={scenario} result={scenario.result as DelayResult} meta={meta} onUpdate={onUpdate} />);

    const group = screen.getByRole("group", { name: "Strategy" });
    const buttons = within(group).getAllByRole("button");
    expect(buttons.map((b) => b.textContent)).toEqual(["Lowest cost", "Protect passengers", "Least delay"]);
    expect(within(group).getByRole("button", { name: "Lowest cost" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/changes which option is\s+recommended, not the numbers/)).toBeInTheDocument();

    const card = document.querySelector('[data-strategy="least_delay"]') as HTMLElement;
    expect(within(card).getByText("Cancel G9521/G9522 round trip")).toBeInTheDocument();
    expect(within(card).getByText("150")).toBeInTheDocument(); // cancelled passengers
    expect(within(card).getByText("200 h")).toBeInTheDocument(); // 12,000 passenger-minutes
    expect(document.querySelector(".strategy-card.active")).toHaveAttribute("data-strategy", "lowest_cost");

    // Kind chips and cancelled flights in the options table.
    const table = screen.getAllByRole("table")[0] as HTMLElement;
    expect(within(table).getByText("Swap")).toBeInTheDocument();
    expect(within(table).getByText("Cancel")).toBeInTheDocument();
    expect(within(table).getByText(/Cancels G9521 SHJ→KHI/)).toBeInTheDocument();

    await userEvent.click(within(group).getByRole("button", { name: "Least delay" }));
    const call = fetchFn.mock.calls.find(([url]) => url.endsWith("/strategy"));
    expect(call?.[0]).toBe("/api/v1/scenarios/s1/strategy");
    expect(JSON.parse(call?.[1]?.body as string)).toEqual({ strategy: "least_delay" });
    expect(onUpdate).toHaveBeenCalledWith(switched);
  });

  it("marks the new strategy's pick as recommended after switching", () => {
    stubFetch(() => []);
    const scenario = delayScenario({ strategy: "least_delay", recommended_key: "cancel:G9521", selected_key: "cancel:G9521" });
    render(<DelayView scenario={scenario} result={scenario.result as DelayResult} meta={meta} onUpdate={() => {}} />);
    expect(document.querySelector(".strategy-card.active")).toHaveAttribute("data-strategy", "least_delay");
    expect(document.querySelector("tr.recommended th")).toHaveTextContent("Cancel G9521/G9522 round trip");
  });

  it("labels passengers by why they need a new flight", () => {
    stubFetch(() => []);
    const pax = {
      rank: 1, pnr: "ABC123", customer_key: "k1", name: "Lina Haddad", pax_type: "AD", route: "SHJ-KHI",
      flight_id: "G9521_202611210900", tier: 3, tier_reason: "", score: 42, non_revenue: false,
      contributions: weights, reason: "", loyalty_tier: null, frequency: null, fare: 300, fare_family: null,
      ancillaries: 0, ssr: null, ssr_source: null, pnr_size: 1, infants: 0, children: 0, assigned_flight: null,
      assigned_flight_id: null, new_departure: null, arrival_delay_minutes: null, onward_ok: null, split: false,
      assignment_reason: "", message: "", group: "cancelled" as const,
    };
    const scenario = delayScenario({ passengers: [pax, { ...pax, customer_key: "k2", name: "Omar Said", group: "missed_connection" }] });
    render(<DelayView scenario={scenario} result={scenario.result as DelayResult} meta={meta} onUpdate={() => {}} />);
    expect(screen.getByText("Flight cancelled")).toBeInTheDocument();
    expect(screen.getByText("Missed connection")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /missed connections and cancelled flights \(2\)/ })).toBeInTheDocument();
  });

  it("shows the agent's recommendation on a scenario the agent produced", () => {
    stubFetch(() => []);
    const scenario = delayScenario({
      agent: { run_id: "r1", source: "ai:claude-opus-5-5", option_key: "swap:A6-ARI", strategy: "lowest_cost",
        reasons: ["Cheapest option by AED 20,000."], risks: ["4 passengers without a seat."],
        checks: ["Crew control confirms legality."] },
    });
    render(<DelayView scenario={scenario} result={scenario.result as DelayResult} meta={meta} onUpdate={() => {}} />);
    const panel = screen.getByRole("heading", { name: /Agent recommendation/ }).closest("section") as HTMLElement;
    expect(within(panel).getByText("AI (Claude)")).toBeInTheDocument();
    expect(within(panel).getByText("Swap: A6-ARI takes over G9520")).toBeInTheDocument();
    expect(within(panel).getByText("Cheapest option by AED 20,000.")).toBeInTheDocument();
    expect(within(panel).getByText("4 passengers without a seat.")).toBeInTheDocument();
    expect(within(panel).getByText("Crew control confirms legality.")).toBeInTheDocument();
    expect(within(panel).getByText(/controller approves it or chooses another option/)).toBeInTheDocument();
  });
});

describe("agent run view", () => {
  const base: AgentRun = {
    id: "r1", flight_id: flight.flight_id, delay_minutes: 150, strategy: null, note: "", status: "RUNNING",
    source: null, fallback_reason: null, trace: [], recommendation: null, error: null, scenario_id: null,
    created_by: "occ", created_at: "2026-11-20T10:00:00Z", finished_at: null,
  };
  const step = (n: number, tool: string, note: string, summary: string, error = false) =>
    ({ n, tool, input: {}, note, summary, error, ms: 120, at: "2026-11-20T10:00:01Z" });
  const steps = [
    step(1, "flight_status", "I start with the flight.", "G9519 MCT-SHJ, 162 booked"),
    step(2, "assess_delay", "Now the options.", "3 options; picks: Lowest cost: swap:A6-ARI"),
    step(3, "passenger_impact", "", "Invalid input for passenger_impact", true),
    step(4, "submit_recommendation", "Done.", "recommends swap:A6-ARI (lowest_cost)"),
  ];
  const recommendation = {
    flight_id: flight.flight_id, delay_minutes: 150, option_key: "swap:A6-ARI", strategy: "lowest_cost" as const,
    reasons: ["Cheapest option."], risks: ["Few seats left."], checks: ["Crew legality."],
  };

  it("shows steps live while running, then the recommendation and the open-scenario button", async () => {
    const sequence: AgentRun[] = [
      { ...base, trace: steps.slice(0, 1) },
      { ...base, trace: steps.slice(0, 3) },
      { ...base, status: "DONE", source: "ai:claude-opus-5-5", trace: steps, recommendation, scenario_id: "s1",
        finished_at: "2026-11-20T10:00:40Z" },
    ];
    let polls = 0;
    stubFetch((url) => {
      if (url.includes("/agent/runs/r1")) return sequence[Math.min(polls++, sequence.length - 1)];
      if (url.includes("/scenarios/s1")) return delayScenario();
      return [];
    });
    const onOpen = vi.fn();
    render(<AgentRunView runId="r1" pollMs={5} onOpenScenario={onOpen} onRetry={() => {}} />);

    expect(await screen.findByText("Checked flight status")).toBeInTheDocument();
    expect(screen.getByText("I start with the flight.")).toBeInTheDocument();
    expect(screen.getByText("G9519 MCT-SHJ, 162 booked")).toHaveClass("muted");
    expect(screen.getAllByText("Working…").length).toBeGreaterThan(0);

    const button = await screen.findByRole("button", { name: "Open scenario to review and approve" });
    expect(screen.getAllByRole("listitem").filter((li) => li.classList.contains("agent-step"))).toHaveLength(4);
    expect(document.querySelector(".agent-step.warn")).toHaveTextContent("Checked the impact on passengers");
    expect(screen.getByText("AI (Claude)")).toBeInTheDocument();
    expect(screen.getByText("Cheapest option.")).toBeInTheDocument();
    expect(screen.getByText("Few seats left.")).toBeInTheDocument();
    expect(screen.getByText("Crew legality.")).toBeInTheDocument();
    expect(await screen.findByText("Swap: A6-ARI takes over G9520")).toBeInTheDocument();
    expect(screen.queryByText(/rule-based planner answered/)).not.toBeInTheDocument();
    await userEvent.click(button);
    expect(onOpen).toHaveBeenCalledWith("s1");
    expect(polls).toBe(3); // polling stops once the run is done
  });

  it("says when the rule-based planner answered instead of the AI", async () => {
    stubFetch((url) => {
      if (url.includes("/agent/runs/r1"))
        return { ...base, status: "DONE", source: "planner", fallback_reason: "AI is not configured (no API key)",
          trace: steps, recommendation, scenario_id: "s1" };
      return delayScenario();
    });
    render(<AgentRunView runId="r1" pollMs={5} onOpenScenario={() => {}} onRetry={() => {}} />);
    expect(await screen.findByText("The AI could not finish (AI is not configured (no API key)), so the rule-based planner answered."))
      .toBeInTheDocument();
    expect(screen.getByText("Rule-based planner")).toBeInTheDocument();
  });

  it("shows a failed run with its error and retries with the same inputs", async () => {
    stubFetch(() => ({ ...base, status: "FAILED", strategy: "least_delay", note: "crew short", trace: steps.slice(0, 1),
      error: "The run could not finish: TimeoutError" }));
    const onRetry = vi.fn();
    render(<AgentRunView runId="r1" pollMs={5} onOpenScenario={() => {}} onRetry={onRetry} />);
    expect(await screen.findByText("The run could not finish: TimeoutError")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledWith({ flight_id: flight.flight_id, delay_minutes: 150, strategy: "least_delay",
      note: "crew short" });
  });
});

describe("starting the agent", () => {
  it("explains a run already in progress in plain words", () => {
    const busy = new ApiError({ title: "Conflict", status: 409, detail: "You already have an agent run in progress" });
    expect(agentStartError(busy)).toMatch(/^You already have an agent run in progress\. Wait for it to finish/);
  });
});

describe("ask the agent from the watchlist", () => {
  it("passes the flight and its planning delay", async () => {
    const risk = {
      flight_id: flight.flight_id, flight_number: "G9519", origin: "MCT", destination: "SHJ", std: "2026-11-21T02:00:00",
      sta: "2026-11-21T03:00:00", tail: "A6-AOH", aircraft_model: "A320-174", p_15: 0.42, p_30: 0.31, p_60: 0.22,
      p_120: 0.08, planning_delay_minutes: 45, risk_band: "high" as const, reasons: [], connecting_pax: 30,
      expected_misconnects: 6.4,
    };
    stubFetch((url) => {
      if (url.includes("/risk/watchlist"))
        return { from_utc: "2026-11-20T00:00:00", days: 7, band: "medium",
          totals: { flights: 1, high: 1, medium: 0, expected_misconnects: 6.4 }, flights: [risk] };
      if (url.includes("/risk/flights/")) return { flight: risk, connections: [] };
      return new Response("{}", { status: 404 });
    });
    const onAgent = vi.fn();
    render(<WatchlistView onAnalyse={() => {}} onAgent={onAgent} busy={false} />);
    await userEvent.click(await screen.findByRole("button", { name: "G9519" }));
    await userEvent.click(screen.getByRole("button", { name: "Ask the agent" }));
    expect(onAgent).toHaveBeenCalledWith(flight.flight_id, 45);
  });
});
