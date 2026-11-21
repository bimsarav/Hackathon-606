import { render, screen } from "@testing-library/react";
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

function stub() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) =>
    new Response(JSON.stringify(url.includes("/presets") ? presets : flights), { status: 200 })));
}
afterEach(() => vi.unstubAllGlobals());

describe("launcher flight lists", () => {
  it("folds the suggested flights away once a flight is chosen and brings them back on request", async () => {
    stub();
    const onDelay = vi.fn();
    render(<Launcher meta={meta} busy={false} onDelay={onDelay} onCancel={() => {}} defaultTab="DELAY" hideTabNav />);
    expect(await screen.findByText(/142 connecting/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Suggested flights" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /G9519/ }));
    expect(onDelay).toHaveBeenCalledWith("G9519_202611210200", 150);
    expect(screen.queryByRole("heading", { name: "Suggested flights" })).not.toBeInTheDocument();
    expect(screen.queryByText(/142 connecting/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Show suggested flights" }));
    expect(screen.getByRole("heading", { name: "Suggested flights" })).toBeInTheDocument();
    expect(screen.getByText(/142 connecting/)).toBeInTheDocument();
  });

  it("shows the search results again after a new search, and starts folded when a scenario is already on screen", async () => {
    stub();
    const { unmount } = render(<Launcher meta={meta} busy={false} onDelay={() => {}} onCancel={() => {}} defaultTab="DELAY" hideTabNav />);
    await userEvent.type(await screen.findByLabelText("Flight / Tail"), "G9520");
    await userEvent.click(screen.getByRole("button", { name: "Search" }));
    await userEvent.click(await screen.findByRole("button", { name: /G9520 SHJ→DXB/ }));
    expect(screen.queryByRole("button", { name: /G9520 SHJ→DXB/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(await screen.findByRole("button", { name: /G9520 SHJ→DXB/ })).toBeInTheDocument();
    unmount();

    render(<Launcher meta={meta} busy={false} onDelay={() => {}} onCancel={() => {}} defaultTab="DELAY" hideTabNav
      active={{ flightId: "G9519_202611210200", flightNumber: "G9519", delay: 150 }} />);
    expect(await screen.findByRole("button", { name: "Show suggested flights" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Suggested flights" })).not.toBeInTheDocument();
  });
});
