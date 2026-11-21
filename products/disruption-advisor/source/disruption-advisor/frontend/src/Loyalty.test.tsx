import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PassengerRow } from "./api";
import { LoyaltyCell } from "./Shared";

const base = { loyalty_tier: null } as unknown as PassengerRow;

describe("LoyaltyCell", () => {
  it("shows tier, recovery priority and the family account", () => {
    render(
      <LoyaltyCell
        p={{ ...base, loyalty_tier: null, loyalty_effective_tier: "Silver", loyalty_effective_priority: "Low",
          loyalty_via_family: true, family_account: true, family_head: false, loyalty_points: null }}
      />,
    );
    expect(screen.getByText(/Silver\* \(Low\)/)).toBeInTheDocument();
    expect(screen.getByText("family account")).toBeInTheDocument();
    expect(screen.getByTitle(/family account's Silver tier/)).toBeInTheDocument();
  });

  it("says when a passenger is not a member, and still reads scenarios saved before the change", () => {
    const { rerender } = render(<LoyaltyCell p={base} />);
    expect(screen.getByText("Not a member")).toBeInTheDocument();
    rerender(<LoyaltyCell p={{ ...base, loyalty_tier: "Gold" }} />);
    expect(screen.getByText("Gold*")).toBeInTheDocument();
  });
});

describe("BookingClass", () => {
  it("shows the class and its level from the fares list, or that it is not in the list", async () => {
    const { BookingClass } = await import("./Shared");
    const { rerender } = render(<BookingClass p={{ ...base, booking_code: "E33", booking_class_level: 0.62 }} />);
    expect(screen.getByText(/class E33 \(62\)/)).toBeInTheDocument();
    rerender(<BookingClass p={{ ...base, booking_code: "DU", booking_class_level: null }} />);
    expect(screen.getByTitle(/not in the fares list/)).toBeInTheDocument();
  });
});
