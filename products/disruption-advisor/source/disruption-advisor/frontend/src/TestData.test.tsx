import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { TestDataReport, TestDataSpec, TestDataStatus } from "./api";
import { TestDataPanel } from "./TestDataPanel";

const spec: TestDataSpec = {
  format: "CSV, comma separated, first row = column names (UTF-8). Times are UTC.",
  limits: { flights: 50, passenger_rows: 3000 },
  notes: ["Uploading again replaces the earlier test data."],
  files: [
    {
      key: "flights", title: "Flights sheet", file_name: "flights.csv", purpose: "One row per flight.",
      template: "flight_number,date\nG9901,2026-11-22\n",
      fields: [
        { name: "flight_number", required: true, example: "G9901", help: "Carrier code and number." },
        { name: "booked_seats", required: false, example: "160", help: "Seats already sold." },
      ],
    },
    {
      key: "passengers", title: "Passengers sheet", file_name: "passengers.csv", purpose: "One row per passenger per flight.",
      template: "pnr,first_name\nAB12CD,Ahmed\n",
      fields: [{ name: "pnr", required: true, example: "AB12CD", help: "Booking reference." }],
    },
  ],
};
const summary = { flights: 2, passenger_segments: 4, passengers: 2 };
const loaded: TestDataStatus = {
  loaded: true, uploaded_by: "occ (OCC)", uploaded_at: "2026-11-21T08:00:00+00:00",
  counts: { flights: 2, passenger_segments: 4, passengers: 2 },
  risk: { scored: 2, connections: 2, reason: null },
  flights: [{ flight_id: "G9901_202611220500", flight_number: "G9901", route: "KHI-SHJ", std: "2026-11-22 05:00",
    sta: "2026-11-22 07:30", tail: "A6-DMA", capacity: 174, booked_seats: 160, passengers: 2 }],
};

function stub(handler: (url: string, init?: RequestInit) => unknown) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => new Response(JSON.stringify(handler(url, init)), { status: 200 }));
  vi.stubGlobal("fetch", fn);
  return fn;
}
afterEach(() => vi.unstubAllGlobals());

const csv = (name: string, text: string) => new File([text], name, { type: "text/csv" });

describe("test data page", () => {
  it("lists the files and columns the evaluator must provide", async () => {
    stub((url) => (url.endsWith("/spec") ? spec : { loaded: false }));
    render(<TestDataPanel />);
    expect(await screen.findByRole("heading", { name: "Flights sheet" })).toBeInTheDocument();
    const columns = screen.getByRole("table", { name: "Flights sheet columns" });
    expect(within(columns).getByText("flight_number")).toBeInTheDocument();
    expect(within(columns).getByText("optional")).toBeInTheDocument();
    expect(screen.getByText(/Up to 50 flights and 3000 passenger rows/)).toBeInTheDocument();
    expect(await screen.findByText(/No test data is loaded/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Check files" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Add to system" })).toBeDisabled();
  });

  it("offers two options, add new flights and edit an existing flight, one shown at a time", async () => {
    stub((url) => (url.endsWith("/spec") ? spec : url.includes("/edits") ? [] : { loaded: false }));
    render(<TestDataPanel />);
    const options = screen.getByRole("group", { name: "Test data options" });
    const add = within(options).getByRole("button", { name: /Add new flights/ });
    const edit = within(options).getByRole("button", { name: /Edit an existing flight/ });
    expect(add).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { name: "Flights sheet" })).toBeInTheDocument();
    await userEvent.click(edit);
    expect(edit).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText("Flight number")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Flights sheet" })).not.toBeInTheDocument();
    await userEvent.click(add);
    expect(screen.getByRole("heading", { name: "Flights sheet" })).toBeInTheDocument();
  });

  it("checks both files, then adds them only after a clean check", async () => {
    const user = userEvent.setup();
    const fetchFn = stub((url, init) => {
      if (url.endsWith("/spec")) return spec;
      if (init?.method === "POST") {
        const commit = JSON.parse(String(init.body)).commit as boolean;
        const report: TestDataReport = { ok: true, committed: commit, errors: [], warnings: ["G9901 has no passengers."],
          summary, ...(commit ? { status: loaded } : {}) };
        return report;
      }
      return { loaded: false };
    });
    render(<TestDataPanel />);
    await screen.findByRole("heading", { name: "Flights sheet" });
    await user.upload(screen.getByLabelText("Upload flights sheet"), csv("flights.csv", "flight_number\nG9901\n"));
    await user.upload(screen.getByLabelText("Upload passengers sheet"), csv("passengers.csv", "pnr\nAB12CD\n"));
    const add = screen.getByRole("button", { name: "Add to system" });
    expect(add).toBeDisabled(); // not checked yet
    await user.click(screen.getByRole("button", { name: "Check files" }));
    expect(await screen.findByText("Files are valid")).toBeInTheDocument();
    expect(screen.getByText("G9901 has no passengers.")).toBeInTheDocument();
    expect(add).toBeEnabled();
    await user.click(add);
    expect(await screen.findByText("Added")).toBeInTheDocument();
    expect(await screen.findByText("Test data loaded")).toBeInTheDocument();
    expect(within(screen.getByRole("table", { name: "Test flights" })).getByText("KHI-SHJ")).toBeInTheDocument();
    expect(screen.getByText(/Delay risk scored with the saved model for 2 flights/)).toBeInTheDocument();
    const posts = fetchFn.mock.calls.filter(([, init]) => init?.method === "POST").map(([, init]) => JSON.parse(String(init?.body)));
    expect(posts.map((p) => p.commit)).toEqual([false, true]);
    expect(posts[0].flights_csv).toContain("G9901");
    expect(posts[0].passengers_csv).toContain("AB12CD");
  });

  it("shows each problem with file, row and column and adds nothing", async () => {
    const user = userEvent.setup();
    stub((url, init) => {
      if (url.endsWith("/spec")) return spec;
      if (init?.method === "POST") {
        const report: TestDataReport = { ok: false, committed: false, warnings: [], summary: { ...summary, flights: 0 },
          errors: [{ file: "flights.csv", row: 3, column: "origin", message: "'KHIX' is not a 3-letter airport code." }] };
        return report;
      }
      return { loaded: false };
    });
    render(<TestDataPanel />);
    await screen.findByRole("heading", { name: "Flights sheet" });
    await user.upload(screen.getByLabelText("Upload flights sheet"), csv("flights.csv", "x\n"));
    await user.upload(screen.getByLabelText("Upload passengers sheet"), csv("passengers.csv", "y\n"));
    await user.click(screen.getByRole("button", { name: "Check files" }));
    const problems = await screen.findByRole("table", { name: "Problems found" });
    expect(within(problems).getByText("origin")).toBeInTheDocument();
    expect(within(problems).getByText("3")).toBeInTheDocument();
    expect(within(problems).getByText(/not a 3-letter airport code/)).toBeInTheDocument();
    expect(screen.getByText(/Nothing was changed/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add to system" })).toBeDisabled();
  });

  it("removes the loaded test data", async () => {
    const user = userEvent.setup();
    const fetchFn = stub((url, init) => {
      if (url.endsWith("/spec")) return spec;
      if (init?.method === "DELETE") return { loaded: false };
      return loaded;
    });
    render(<TestDataPanel />);
    await user.click(await screen.findByRole("button", { name: "Remove test data" }));
    await waitFor(() => expect(screen.getByText(/No test data is loaded/)).toBeInTheDocument());
    expect(fetchFn.mock.calls.some(([, init]) => init?.method === "DELETE")).toBe(true);
  });
});
