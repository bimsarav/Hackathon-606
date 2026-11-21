import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CrewCheck, RecoveryOption } from "./api";
import { CrewFdpAlerts } from "./CrewFdpAlerts";
import { CrewSection } from "./DelayView";

const over = {
  flight_id: "G9294_202611210830", flight_number: "G9294", origin: "SHJ", destination: "TBS",
  new_std: "2026-11-21T11:56:00", delay_minutes: 206, headroom_minutes: 200, minutes_left: -6, crew_type: "CP",
  source: "estimated" as const, status: "over" as const,
};
const check = (c: Partial<CrewCheck>): CrewCheck => ({
  status: "over", flights_checked: 3, flights_over: 1, flights_tight: 0, flights_unknown: 0, estimated: 1,
  worst: over, flights: [over], ...c,
});
const option = (key: string, label: string, crew: CrewCheck): RecoveryOption =>
  ({ key, label, crew } as unknown as RecoveryOption);
const absorb = option("absorb", "Absorb the delay on A6-ARD", check({}));
const swap = option("swap:A6-ANO", "Swap: A6-ANO takes over G9294",
  check({ status: "ok", flights_over: 0, worst: { ...over, minutes_left: 97, status: "ok" }, flights: [] }));

describe("CrewFdpAlerts", () => {
  it("is hidden when no option breaches the maximum FDP", () => {
    const { container } = render(<CrewFdpAlerts options={[swap]} selectedKey={swap.key} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("alerts the breach of the selected option with the flight, crew and minutes over", () => {
    render(<CrewFdpAlerts options={[swap, absorb]} selectedKey="absorb" />);
    expect(screen.getByRole("heading", { name: "Crew FDPs" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("the selected option would take a crew past its maximum flight duty period");
    expect(screen.getByText("G9294")).toBeInTheDocument();
    expect(screen.getByText("Captain")).toBeInTheDocument();
    expect(screen.getByText("6 min over")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull(); // alert only: no recovery actions
  });

  it("still alerts other options when the selected one is legal", () => {
    render(<CrewFdpAlerts options={[swap, absorb]} selectedKey={swap.key} />);
    expect(screen.getByRole("alert")).toHaveTextContent("1 of 2 options would take a crew past");
    expect(screen.getByText("Absorb the delay on A6-ARD")).toBeInTheDocument();
  });
});

describe("CrewSection", () => {
  it("says all checked flights are within limits when none is tight (same statement as the tile)", () => {
    render(<CrewSection option={swap} />);
    expect(screen.getByText(/All 3 delayed flight\(s\) checked are within the duty limits/)).toBeInTheDocument();
    expect(screen.getByText(/tightest: G9294, 97 min left, estimated duty/)).toBeInTheDocument();
    expect(screen.queryByText(/No crew data/)).not.toBeInTheDocument();
  });

  it("says there is no crew data only when no flight could be checked", () => {
    render(<CrewSection option={option("x", "X", check({ status: "unknown", flights_checked: 0, estimated: 0, worst: null, flights: [] }))} />);
    expect(screen.getByText(/No crew data for the flights of this option/)).toBeInTheDocument();
  });
});
