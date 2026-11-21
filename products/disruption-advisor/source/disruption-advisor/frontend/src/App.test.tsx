import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Meta, Scenario } from "./api";
import { App } from "./App";
import { CancelView } from "./CancelView";
import { CarrierTail } from "./CarrierTail";
import { DelayView } from "./DelayView";
import { WatchlistView } from "./WatchlistView";
import { aed, minutes, utc } from "./format";

const weights = { loyalty: 20, frequency: 15, fare_value: 20, ancillaries: 10, journey: 20, booking: 15 };
const meta: Meta = {
  user: { username: "occ", role: "OCC" },
  now_utc: "2026-11-20T00:00:00",
  horizon_days: 7,
  ai_enabled: false,
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
const passenger = {
  rank: 1, pnr: "ABC123", customer_key: "abcdef0123456789", name: "Lina Haddad", pax_type: "AD", route: "SHJ-CAI",
  flight_id: "G9201_202611211200", tier: 1, tier_reason: "Mandated care: WCHR", score: 42, non_revenue: false,
  contributions: { loyalty: 10, frequency: 5, fare_value: 12, ancillaries: 0, journey: 0, booking: 15 },
  reason: "Tier 1 (Mandated care: WCHR). Score 42/100.", loyalty_tier: "Gold", frequency: "frequent", fare: 650,
  fare_family: "Value", ancillaries: 40, ssr: "WCHR", ssr_source: "synthetic", pnr_size: 1, infants: 0, children: 0,
  assigned_flight: "G9203", assigned_flight_id: "G9203_202611211800", new_departure: "2026-11-21T18:00:00",
  arrival_delay_minutes: 360, onward_ok: null, split: false, assignment_reason: "Seats available",
  message: "Dear customer, your flight G9201 is cancelled.",
};

function stubFetch(handler: (url: string) => unknown) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify(handler(url)), { status: 200 })));
}

beforeEach(() => sessionStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe("carrier tail", () => {
  it("shows the airline tail for known carriers and nothing for bus legs", () => {
    const { container, rerender } = render(<CarrierTail flightNumber="G9519" />);
    expect(container.querySelector("img")?.getAttribute("src")).toBe("/brand/tails/G9.svg");
    expect(container.querySelector("img")?.getAttribute("alt")).toBe("");
    rerender(<CarrierTail flightNumber="02123" />);
    expect(container.querySelector("img")).toBeNull();
  });
});

describe("format", () => {
  it("formats UTC times, minutes and money", () => {
    expect(utc("2026-11-21T13:55:00")).toBe("21 Nov 13:55Z");
    expect(minutes(150)).toBe("2 h 30 min");
    expect(aed(70875)).toBe("AED 70,875");
  });
});

describe("App", () => {
  it("asks for sign-in and shows the API error on a wrong password", async () => {
    vi.stubGlobal("fetch", vi.fn(async () =>
      new Response(JSON.stringify({ title: "Unauthorized", status: 401, detail: "Wrong user name or password" }), { status: 401 })));
    render(<App />);
    await userEvent.type(screen.getByLabelText("User name"), "occ");
    await userEvent.type(screen.getByLabelText("Password"), "bad");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Wrong user name or password");
  });

  it("signs in and shows the scenario launcher with suggestions", async () => {
    stubFetch((url) => {
      if (url.includes("/auth/login")) return { token: "t", username: "occ", role: "OCC", expires_at: "2099-01-01T00:00:00Z" };
      if (url.includes("/meta")) return meta;
      if (url.includes("/presets"))
        return { delay: [{ flight_id: flight.flight_id, flight_number: "G9519", origin: "MCT", destination: "SHJ",
          std: flight.std, tail: "A6-AOH", is_demo: false, turn_minutes: 55, connecting_pax: 142 }], cancel: [] };
      if (url.includes("/scenarios")) return [];
      return {};
    });
    render(<App />);
    await userEvent.type(screen.getByLabelText("User name"), "occ");
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Start with a disruption")).toBeInTheDocument();
    expect(await screen.findByText(/142 connecting/)).toBeInTheDocument();
    expect(screen.getByText("AI off: template explanations")).toBeInTheDocument();
  });
});

describe("result views", () => {
  it("shows the recommended recovery option and its saving", () => {
    stubFetch(() => []);
    const scenario: Scenario = {
      id: "s1", kind: "DELAY", flight_id: flight.flight_id, delay_minutes: 150, weights, created_by: "occ",
      created_at: "2026-11-20T10:00:00",
      result: {
        type: "DELAY", flight, delay_minutes: 150, recommended_key: "swap:A6-ARI",
        explanation: { text: "Swap is cheaper.", source: "template" }, passengers: [], rebooking: null,
        misconnections: [], assumptions: ["Costs are assumed."],
        options: [
          { key: "swap:A6-ARI", label: "Swap: A6-ARI takes over G9520", total_delay_minutes: 150, legs_delayed: 1,
            delayed_passengers: 162, misconnects: 33, connections_checked: 142, eu261_compensation_eur: 0, cost_aed: 70875,
            cost_breakdown: {}, legs: [] },
          { key: "absorb", label: "Absorb the delay on A6-AOH", total_delay_minutes: 480, legs_delayed: 5,
            delayed_passengers: 800, misconnects: 90, connections_checked: 300, eu261_compensation_eur: 0, cost_aed: 222600,
            cost_breakdown: {}, legs: [] },
        ],
      },
    };
    render(<DelayView scenario={scenario} result={scenario.result as never} meta={meta} onUpdate={() => {}} />);
    expect(screen.getAllByText("Swap: A6-ARI takes over G9520").length).toBeGreaterThan(0);
    expect(screen.getByText("saves AED 151,725 vs worst option")).toBeInTheDocument();
    expect(screen.getByText("Template text")).toBeInTheDocument();
  });

  it("lists cancelled-flight passengers with tier and recommended flight", () => {
    stubFetch(() => []);
    const scenario: Scenario = {
      id: "s2", kind: "CANCEL", flight_id: "G9201_202611211200", delay_minutes: null, weights, created_by: "pcu",
      created_at: "2026-11-20T10:00:00",
      result: {
        type: "CANCEL", flight, explanation: { text: "Rebook by priority.", source: "template" },
        passengers: [passenger], tier_counts: { "1": 1, "2": 0, "3": 0, non_revenue: 0 },
        rebooking: { alternatives: [], protected: 1, unprotected: 0, groups_split: 0 }, assumptions: [],
        cost_aed: {}, cost_total_aed: 1000, eu261_per_passenger_eur: 0, onward_connections: 0, solver_status: "OPTIMAL",
        aircraft_follow_on: null,
      },
    };
    render(<CancelView scenario={scenario} result={scenario.result as never} meta={meta} onUpdate={() => {}} />);
    expect(screen.getByText("Lina Haddad")).toBeInTheDocument();
    expect(screen.getByText("G9203")).toBeInTheDocument();
    expect(screen.getAllByText("Care").length).toBeGreaterThan(0);
  });
});

describe("WatchlistView", () => {
  const risk = {
    flight_id: flight.flight_id, flight_number: "G9519", origin: "MCT", destination: "SHJ", std: "2026-11-21T02:00:00",
    sta: "2026-11-21T03:00:00", tail: "A6-AOH", aircraft_model: "A320-174", p_15: 0.42, p_30: 0.31, p_60: 0.22,
    p_120: 0.08, planning_delay_minutes: 45, risk_band: "high" as const,
    reasons: [{ feature: "tail_delay", text: "The aircraft was late on its earlier flights", contribution: 0.4 }],
    connecting_pax: 30, expected_misconnects: 6.4,
  };

  it("lists flights at risk, opens one with reasons and connections, and starts a scenario", async () => {
    stubFetch((url) => {
      if (url.includes("/risk/watchlist"))
        return { from_utc: "2026-11-20T00:00:00", days: 7, band: "medium",
          totals: { flights: 1, high: 1, medium: 0, expected_misconnects: 6.4 }, flights: [risk] };
      if (url.includes("/risk/flights/"))
        return { flight: risk, connections: [{ pnr: "ABC123", passenger_id: "P1", outbound_flight_id: "G9201_202611211200",
          outbound_flight_number: "G9201", hub: "SHJ", final_destination: "CAI", connection_minutes: 95, mct_minutes: 60,
          default_mct: false, slack_minutes: 35, misconnect_risk: 0.37 }] };
      throw new Error("no model card");
    });
    const onAnalyse = vi.fn();
    render(<WatchlistView onAnalyse={onAnalyse} busy={false} />);
    expect(await screen.findByText("22%")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "G9519" }));
    expect(await screen.findByText("The aircraft was late on its earlier flights", { selector: "li" })).toBeInTheDocument();
    expect(await screen.findByText("37%")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Analyse a 45 min delay/ }));
    expect(onAnalyse).toHaveBeenCalledWith(flight.flight_id, 45);
  });

  it("shows the API error when the risk data is not available", async () => {
    vi.stubGlobal("fetch", vi.fn(async () =>
      new Response(JSON.stringify({ title: "Unavailable", status: 503, detail: "Delay-risk data is not available yet" }), { status: 503 })));
    render(<WatchlistView onAnalyse={() => {}} busy={false} />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
