"""Care while waiting: meals by waiting time, hotel + transport for long or overnight waits, flags, refund option."""

from datetime import datetime, timedelta

from app.engine.care import CareRules, care_for

RULES = CareRules()
NOON = datetime(2026, 11, 22, 8, 0)  # 12:00 in Dubai (UTC+4)


def _care(wait_h: float, start: datetime = NOON, **kw: object):  # type: ignore[no-untyped-def]
    args = {"has_seat": True, "transfer": False, "ssr": None, "infants": 0, "new_flight": "G9955"} | kw
    return care_for(RULES, start, start + timedelta(hours=wait_h), "Asia/Dubai", **args)  # type: ignore[arg-type]


def test_short_wait_needs_no_care() -> None:
    care = _care(1.5)
    assert (care.meals, care.hotel, care.refund_option) == (0, False, False)
    assert care.summary == "no care needed"


def test_daytime_wait_gets_meals_by_length() -> None:
    assert _care(3).meals == 1
    care = _care(6)
    assert care.meals == 1
    assert care.hotel is False
    assert care.refund_option is True  # 5 h or more


def test_long_wait_gets_hotel_transport_and_capped_meals() -> None:
    care = _care(19)
    assert care.hotel is True
    assert care.transport is True
    assert care.meals == 4
    assert care.cost(RULES) == 4 * 50 + 350 + 2 * 60
    assert "hotel room" in care.message_text()


def test_overnight_wait_gets_a_hotel_even_if_short() -> None:
    late_evening = datetime(2026, 11, 22, 19, 0)  # 23:00 Dubai, departs 05:30 Dubai
    care = _care(6.5, start=late_evening)
    assert care.hotel is True


def test_no_seat_means_next_day_care_and_refund_option() -> None:
    care = care_for(
        RULES, NOON, None, "Asia/Dubai", has_seat=False, transfer=True, ssr=None, infants=0, new_flight=None
    )
    assert care.hotel is True
    assert care.refund_option is True
    assert any("transit visa" in f for f in care.flags)


def test_flags_for_assistance_pregnancy_and_infants() -> None:
    assert any("Re-book WCHR" in f for f in _care(3, ssr="WCHR").flags)
    preg = _care(10, ssr="PREG").flags
    assert any("fit-to-fly" in f for f in preg)
    assert any("Infant" in f for f in _care(10, infants=1).flags)
    assert not any("transit visa" in f for f in _care(10, transfer=False).flags)
