import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FlightEditor } from "./FlightEditor";

const editable = {
  flight: { flight_id: "G9519_202611210200", flight_number: "G9519", origin: "DAC", destination: "SHJ", std: "2026-11-21T02:00:00",
    sta: "2026-11-21T07:00:00", std_hhmm: "02:00", sta_hhmm: "07:00", tail: "A6-ARD", capacity: 174, booked_seats: 168 },
  passengers: [
    { customer_key: "k1", pnr: "AB12CD", passenger_id: "PAX1", pax_type: "AD", fare_family: "Value", fare: 500, ssr: null, loyalty_tier: "none", frequency: "regular" },
    { customer_key: "k2", pnr: "EF34GH", passenger_id: "PAX2", pax_type: "AD", fare_family: "Basic", fare: 300, ssr: null, loyalty_tier: "Gold", frequency: "frequent" },
  ],
  edited: false,
};

function stub() {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    let body: unknown = [];
    if (url.includes("/test-data/edits")) body = [];
    else if (url.includes("/test-data/flights/") && init?.method === "PUT") body = { saved: true };
    else if (url.includes("/test-data/flights/")) body = editable;
    else if (url.includes("/flights?")) body = [{ ...editable.flight, airline: "G9", booked_pax: 168, aircraft_model: "A320", capacity_source: "x" }];
    return new Response(JSON.stringify(body), { status: 200 });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}
afterEach(() => vi.unstubAllGlobals());

describe("edit an existing flight", () => {
  it("opens a flight in a table, edits fields and passengers, and saves the edits", async () => {
    const fetchFn = stub();
    render(<FlightEditor />);
    await userEvent.type(screen.getByLabelText("Flight number"), "G9519");
    await userEvent.click(await screen.findByRole("button", { name: /G9519 DAC→SHJ/ }, { timeout: 2000 }));
    const table = await screen.findByRole("table", { name: "Passengers of the flight" });
    expect(within(table).getAllByRole("row")).toHaveLength(3);

    await userEvent.clear(screen.getByLabelText("Seats sold"));
    await userEvent.type(screen.getByLabelText("Seats sold"), "174");
    await userEvent.selectOptions(within(table).getAllByLabelText("Loyalty tier")[0] as HTMLElement, "Platinum");
    await userEvent.type(within(table).getAllByLabelText("Special service")[0] as HTMLElement, "wchr");
    await userEvent.click(screen.getByLabelText("Remove EF34GH"));
    await userEvent.click(screen.getByRole("button", { name: "Add passenger" }));
    expect(screen.getByText(/2 passengers kept of 3 listed \(incl\. added\)/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText(/now uses your edits/)).toBeInTheDocument();
    const put = fetchFn.mock.calls.find(([, init]) => init?.method === "PUT");
    const body = JSON.parse(String(put?.[1]?.body));
    expect(body.flight.booked_seats).toBe(174);
    expect(body.passengers[0]).toMatchObject({ customer_key: "k1", loyalty_tier: "Platinum", ssr: "WCHR", remove: false });
    expect(body.passengers[1]).toMatchObject({ customer_key: "k2", remove: true });
    expect(body.passengers[2]).toMatchObject({ customer_key: null, pnr: "NEW01" });
  });
});
