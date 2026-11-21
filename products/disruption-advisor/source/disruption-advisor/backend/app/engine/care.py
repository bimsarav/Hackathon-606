"""Passenger care while waiting for the new flight.

Rules (configurable; assumptions to validate with the airline, labelled in the UI):
  wait < 2 h                      no care
  wait 2 h or more                meal vouchers, one per 4 h of waiting (at least one, at most four)
  wait 8 h or more, or overnight  hotel room and airport-hotel transport as well
  overnight = the wait overlaps the local night (01:00-05:00 at the station) by at least 2 hours
  no seat within the rebooking window: treated as an overnight wait (next-day flight)
Flags:
  transfer passenger who needs a hotel  -> check the transit visa, or use an airside / transit hotel
  special assistance (WCHR, MEDA, ...)   -> re-book the assistance on the new flight; PREG: check fit-to-fly
  infant in the booking                  -> infant supplies, priority hotel room
Option offered:
  wait 5 h or more, or no seat           -> refund and free return to origin, or a free date change
EU261 Art. 9 sets meals in proportion to the wait and a hotel when a night's stay is needed, but only for EU/EEA/CH
departures. For other stations these rules are airline policy, so the thresholds are settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ASSISTANCE_SSRS = frozenset({"WCHR", "WCHS", "WCHC", "BLND", "DEAF", "MEDA", "PREG"})


@dataclass(frozen=True)
class CareRules:
    meal_after_minutes: int = 120
    meal_every_minutes: int = 240
    hotel_after_minutes: int = 480
    refund_offer_after_minutes: int = 300
    meal_aed: float = 50.0
    hotel_aed: float = 350.0
    transport_aed: float = 60.0


@dataclass
class Care:
    wait_minutes: int | None
    meals: int = 0
    hotel: bool = False
    transport: bool = False
    refund_option: bool = False
    flags: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        parts = []
        if self.hotel:
            parts.append("hotel room")
        if self.transport:
            parts.append("transport")
        if self.meals:
            parts.append(f"{self.meals} meal voucher{'s' if self.meals > 1 else ''}")
        return " + ".join(parts) if parts else "no care needed"

    def cost(self, rules: CareRules) -> float:
        return self.meals * rules.meal_aed + self.hotel * rules.hotel_aed + self.transport * rules.transport_aed * 2

    def message_text(self) -> str:
        if not (self.meals or self.hotel):
            return ""
        offer = []
        if self.hotel:
            offer.append("a hotel room")
        if self.transport:
            offer.append("transport to and from the hotel")
        if self.meals:
            offer.append("meal vouchers")
        text = (
            "While you wait, we will provide "
            + (", ".join(offer[:-1]) + " and " + offer[-1] if len(offer) > 1 else offer[0])
            + "."
        )
        if self.refund_option:
            text += " If you prefer, you can have a refund and a free flight back to your origin, or change the date."
        return text


def _overnight(start: datetime, end: datetime, tz_name: str | None) -> bool:
    """True when the wait overlaps the local night (01:00-05:00 at the station) by at least 2 hours."""
    try:
        tz = ZoneInfo(tz_name) if tz_name else ZoneInfo("UTC")
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    utc = ZoneInfo("UTC")
    local_start = start.replace(tzinfo=utc).astimezone(tz)
    local_end = end.replace(tzinfo=utc).astimezone(tz)
    night_start = local_start.replace(hour=1, minute=0, second=0, microsecond=0)
    if local_start.hour >= 5:
        night_start += timedelta(days=1)
    night_end = night_start + timedelta(hours=4)
    overlap = min(local_end, night_end) - max(local_start, night_start)
    return overlap >= timedelta(hours=2)


def care_for(
    rules: CareRules,
    waiting_from: datetime | None,
    new_departure: datetime | None,
    station_tz: str | None,
    *,
    has_seat: bool,
    transfer: bool,
    ssr: str | None,
    infants: int,
    new_flight: str | None,
) -> Care:
    if not has_seat or waiting_from is None or new_departure is None:
        care = Care(wait_minutes=None, meals=3, hotel=True, transport=True, refund_option=True)
    else:
        wait = max(int((new_departure - waiting_from).total_seconds() // 60), 0)
        overnight = wait >= rules.meal_after_minutes and _overnight(waiting_from, new_departure, station_tz)
        hotel = wait >= rules.hotel_after_minutes or overnight
        meals = 0 if wait < rules.meal_after_minutes else min(max(wait // rules.meal_every_minutes, 1), 4)
        care = Care(
            wait_minutes=wait,
            meals=meals,
            hotel=hotel,
            transport=hotel,
            refund_option=wait >= rules.refund_offer_after_minutes,
        )
    if care.hotel and transfer:
        care.flags.append("Transfer passenger: check the transit visa, or use an airside / transit hotel")
    if ssr in ASSISTANCE_SSRS:
        target = new_flight or "the new flight"
        care.flags.append(f"Re-book {ssr} assistance on {target}")
        if ssr == "PREG":
            care.flags.append("Pregnancy: check fit-to-fly for the new date")
    if infants > 0 and care.hotel:
        care.flags.append("Infant: supplies and a priority hotel room")
    return care
