import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Meta, RecoveryOption } from "./api";
import { buildBars, RotationBoard } from "./RotationBoard";

const leg = (id: string, std: string, newStd: string, newSta: string, by: string, sched: string, delay: number) => ({
  flight_id: id, flight_number: id.slice(0, 5), origin: "SHJ", destination: "SHJ", std, new_std: newStd,
  new_sta: newSta, delay_minutes: delay, operated_by: by, scheduled_tail: sched, booked_pax: 100,
});

const swap: RecoveryOption = {
  key: "swap:A6-BBB", label: "Swap: A6-BBB takes over G9002", total_delay_minutes: 150, legs_delayed: 1,
  delayed_passengers: 100, misconnects: 3, connections_checked: 10, eu261_compensation_eur: 0, cost_aed: 1000,
  cost_breakdown: {},
  legs: [
    leg("G9001_202611210200", "2026-11-21T02:00:00", "2026-11-21T04:30:00", "2026-11-21T07:30:00", "A6-AAA", "A6-AAA", 150),
    leg("G9002_202611210830", "2026-11-21T08:30:00", "2026-11-21T08:30:00", "2026-11-21T11:00:00", "A6-BBB", "A6-AAA", 0),
  ],
};

describe("RotationBoard", () => {
  it("puts legs on the scheduled aircraft before and on the operating aircraft after", () => {
    const before = buildBars(swap, "G9001_202611210200", false);
    const after = buildBars(swap, "G9001_202611210200", true);
    expect(before.map((b) => [b.tail, b.kind])).toEqual([["A6-AAA", "planned"], ["A6-AAA", "planned"]]);
    expect(after.map((b) => [b.tail, b.kind])).toEqual([["A6-AAA", "disrupted"], ["A6-BBB", "moved"]]);
    // block time is kept: the planned bar of the delayed flight ends 3 h after its scheduled departure
    const [first] = before;
    expect(first && first.end - first.start).toBe(3 * 3600e3);
  });

  it("renders both boards with a summary of the change", () => {
    const meta = { horizon_days: 7, min_turn_minutes: { default: 36, by_station: { SHJ: 51 } } } as unknown as Meta;
    render(<RotationBoard option={swap} disruptedId="G9001_202611210200" meta={meta} />);
    expect(screen.getByText(/1 flight\(s\) leave late and 1 flight\(s\) move to another aircraft/)).toBeInTheDocument();
    expect(screen.getByText("Rotation as planned")).toBeInTheDocument();
    expect(screen.getByText("With this option")).toBeInTheDocument();
    expect(screen.getAllByText("A6-BBB").length).toBe(2);
  });
});
