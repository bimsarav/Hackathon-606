import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Meta } from "./api";
import { Launcher } from "./Launcher";

const weights = { loyalty: 20, frequency: 15, fare_value: 20, ancillaries: 10, journey: 20, booking: 15 };
const meta = { user: { username: "occ", role: "OCC" }, default_weights: weights } as unknown as Meta;
const presets = {
  delay: [{ flight_id: "G9519_202611210200", flight_number: "G9519", origin: "MCT", destination: "SHJ", std: "2026-11-21T02:00:00",
    tail: "A6-AOH", is_demo: false, turn_minutes: 55, connecting_pax: 142 }],
  cancel: [],
};
const flights = [{ flight_id: "G9520_202611210400", flight_number: "G9520", airline: "G9", tail: "A6-ARI", origin: "SHJ", destination: "DXB",
  std: "2026-11-21T04:00:00", sta: "2026-11-21T06:00:00", capacity: 174, booked_seats: 100, booked_pax: 100, aircraft_model: "A320", capacity_source: "x" }];

const curve = { mode: "planning", p: { "5": 0.5, "15": 0.3, "30": 0.2, "60": 0.1, "120": 0.02, "180": 0.01 }, expected_minutes: 20, planning_delay_minutes: null, risk_band: "low" };
const prediction = { departure: curve, arrival: curve };

function stub() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) =>
    new Response(JSON.stringify(url.includes("/presets") ? presets : url.includes("/predict") ? prediction : flights), { status: 200 })));
}
afterEach(() => vi.unstubAllGlobals());

describe("launcher flight lists", () => {
  it("folds the suggested flights away once a flight is chosen and brings them back on request", async () => {
    stub();
    const onDelay = vi.fn();
    render(<Launcher meta={meta} busy={false} onDelay={onDelay} onCancel={() => {}} defaultTab="DELAY" hideTabNav />);
    expect(await screen.findByText(/142 conn/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Suggested flights" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Suggested flights" })).toHaveClass("preset-chips"); // chips by default
    expect(screen.queryByLabelText(/Advanced search/)).not.toBeInTheDocument(); // hidden for now

    await userEvent.click(screen.getByRole("button", { name: /G9519/ }));
    expect(onDelay).toHaveBeenCalledWith("G9519_202611210200", 150);
    expect(screen.queryByRole("heading", { name: "Suggested flights" })).not.toBeInTheDocument();
    expect(screen.queryByText(/142 conn/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Change flight or search" }));
    expect(screen.getByRole("heading", { name: "Suggested flights" })).toBeInTheDocument();
    expect(screen.getByText(/142 conn/)).toBeInTheDocument();
  });

  it("shows recent scenarios as chips that reopen them, and the suggestions as a list on request", async () => {
    stub();
    const onOpenRecent = vi.fn();
    const recent = [{ id: "s9", kind: "DELAY" as const, flight_id: "G9502_202611201835", delay_minutes: 60, created_by: "occ", created_at: "2026-11-21T10:00:00" }];
    render(<Launcher meta={meta} busy={false} onDelay={() => {}} onCancel={() => {}} defaultTab="DELAY" hideTabNav recent={recent} onOpenRecent={onOpenRecent} />);
    await userEvent.click(within(screen.getByRole("group", { name: "Recent scenarios" })).getByRole("button", { name: "G9502 · +60m" }));
    expect(onOpenRecent).toHaveBeenCalledWith("s9");
    await screen.findByText(/142 conn/);
    await userEvent.click(screen.getByRole("button", { name: "Show as list" }));
    expect(await screen.findByText(/turn 55 min · 142 connecting/)).toBeInTheDocument(); // the full card
  });

  it("searches as you type, shows one list (results or suggestions) and filters by day", async () => {
    stub();
    render(<Launcher meta={{ ...meta, now_utc: "2026-11-20T00:00:00", horizon_days: 7 } as Meta} busy={false} onDelay={() => {}} onCancel={() => {}} defaultTab="DELAY" hideTabNav />);
    expect(await screen.findByRole("heading", { name: "Suggested flights" })).toBeInTheDocument();
    const days = screen.getByRole("group", { name: "Departure day (UTC)" });
    expect(within(days).getAllByRole("button").filter((b) => b.classList.contains("chip-btn")).map((b) => b.textContent)).toEqual(["All", "Thu 19", "Fri 20", "Sat 21", "Sun 22", "Mon 23", "Tue 24", "Wed 25", "Thu 26", "Fri 27"]);
    await userEvent.type(screen.getByLabelText("Flight number"), "G95");
    expect(await screen.findByRole("heading", { name: /1 flights match “G95”/ }, { timeout: 2000 })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Suggested flights" })).not.toBeInTheDocument(); // one list at a time
    await userEvent.click(within(days).getByRole("button", { name: "Fri 20" }));
    expect(screen.getByRole("heading", { name: /0 flights match/ })).toBeInTheDocument(); // the flight leaves on the 21st
    await userEvent.click(screen.getByRole("button", { name: /Clear search/ }));
    expect(screen.getByRole("heading", { name: "Suggested flights" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Origin")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /More filters/ }));
    expect(screen.getByLabelText("Origin")).toBeInTheDocument();
    await userEvent.click(within(days).getByRole("button", { name: "All" }));
    // the main box matches flight numbers only; airports and tails are filters
    await userEvent.type(screen.getByLabelText("Flight number"), "SHJ");
    expect(await screen.findByRole("heading", { name: /0 flights match “SHJ”/ }, { timeout: 2000 })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Clear search/ }));
    await userEvent.type(screen.getByLabelText("Aircraft (tail)"), "A6-ARI");
    expect(await screen.findByRole("heading", { name: /1 flights match “A6-ARI”/ }, { timeout: 2000 })).toBeInTheDocument();
  });

  it("shows the search results again after a new search, and starts folded when a scenario is already on screen", async () => {
    stub();
    const { unmount } = render(<Launcher meta={meta} busy={false} onDelay={() => {}} onCancel={() => {}} defaultTab="DELAY" hideTabNav />);
    await userEvent.type(await screen.findByLabelText("Flight number"), "G9520");
    await userEvent.click(screen.getByRole("button", { name: "Search" }));
    await userEvent.click(await screen.findByRole("button", { name: /G9520 SHJ→DXB/ }));
    expect(screen.queryByRole("button", { name: /G9520 SHJ→DXB/ })).not.toBeInTheDocument();
    expect(screen.getByText("G9520")).toBeInTheDocument(); // the search folded to one line naming the flight
    expect(screen.queryByRole("button", { name: "Search" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Change flight or search" }));
    await userEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(await screen.findByRole("button", { name: /G9520 SHJ→DXB/ })).toBeInTheDocument();
    unmount();

    render(<Launcher meta={meta} busy={false} onDelay={() => {}} onCancel={() => {}} defaultTab="DELAY" hideTabNav
      active={{ flightId: "G9519_202611210200", flightNumber: "G9519", delay: 150 }} />);
    expect(await screen.findByRole("button", { name: "Change flight or search" })).toBeInTheDocument();
    expect(screen.getByLabelText(/Delay:/)).toBeInTheDocument(); // the slider stays in the folded line to re-run
    expect(screen.queryByRole("heading", { name: "Suggested flights" })).not.toBeInTheDocument();
  });
});
