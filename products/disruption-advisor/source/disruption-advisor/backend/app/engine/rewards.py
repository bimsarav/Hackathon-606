"""Passenger goodwill rewards for a disrupted flight (phase 5, ADR 0012, docs/architecture/REWARDS_DESIGN.md).

For every passenger of the flight:
  severity   0-100  how badly the disruption hit this passenger (delay or cancellation, a missed connection, the
                    wait it caused, a vulnerable passenger)
  value      0-100  where the recovery-priority score (loyalty, frequency, fare, ancillaries, journey, family
                    booking) stands among the passengers of the flight
  target     AED    max target x severity x (0.4 + 0.6 x value)
  preference 0-1    per reward type, by proxy rules (no redemption history exists, so these are assumptions)
The best eligible reward within the target is chosen by utility = severity x value x preference x sqrt(cost); if the
plan costs more than the budget, the step that loses the least utility per AED saved is downgraded, one at a time,
until it fits. Statutory care (meals and hotel under the care rules, EU261) is separate and never taken from this
budget. The plan only recommends: a person approves it, and nothing is sent to passengers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Any

from app.engine import priority

DIGITAL_CHANNELS = frozenset({"Web", "IOS", "ANDROID", "SITECORE"})
PRICE_SENSITIVE_FAMILIES = frozenset({"Basic", "Value"})
PREMIUM_FAMILIES = frozenset({"Ultimate"})
HIGH_FREQUENCY = frozenset({"frequent"})
REGULAR_OR_BETTER = frozenset({"regular", "frequent"})
TOP_TIERS = frozenset({"Gold", "Platinum"})

MEAL, VOUCHER, LOUNGE, MILES, TICKET = "MEAL", "VOUCHER", "LOUNGE", "MILES", "TICKET"
TYPE_LABEL = {
    MEAL: "Meal voucher",
    VOUCHER: "Shopping voucher",
    LOUNGE: "Lounge pass",
    MILES: "Loyalty miles",
    TICKET: "Free ticket",
}


@dataclass(frozen=True)
class RewardRules:
    """Assumed defaults (AED), to confirm with the airline."""

    max_target_aed: float = 600.0
    meal_aed: float = 50.0
    voucher_aed: tuple[float, ...] = (100.0, 200.0, 400.0)
    lounge_aed: float = 120.0
    miles: tuple[tuple[int, float], ...] = ((5000, 100.0), (10000, 200.0), (20000, 400.0))  # (miles, AED value)
    ticket_aed: float = 600.0
    meal_min_minutes: int = 60
    lounge_min_minutes: int = 120
    ticket_min_severity: float = 75.0
    non_revenue_gets_reward: bool = False


@dataclass(frozen=True)
class Option:
    kind: str
    label: str
    cost: float
    detail: str


@dataclass
class Person:
    """Everything the plan needs about one passenger."""

    pnr: str
    customer_key: str
    passenger_id: str | None
    route: str
    tier: int
    value: float
    severity: float
    severity_reasons: list[str]
    disrupted_minutes: int
    loyalty_member: bool
    non_revenue: bool
    prefs: dict[str, float] = field(default_factory=dict)
    pref_reasons: dict[str, list[str]] = field(default_factory=dict)
    accept: dict[tuple[str, float], float] = field(default_factory=dict)  # trained model: P(accept) per option


def severity(
    delay_minutes: int | None, cancelled: bool, missed: bool, wait_minutes: int | None, vulnerable: bool
) -> tuple[float, list[str]]:
    """0-100 and the reasons behind it."""
    reasons: list[str] = []
    if cancelled:
        score = 60.0
        reasons.append("flight cancelled (+60)")
    else:
        score = min((delay_minutes or 0) / 240.0, 1.0) * 50.0
        reasons.append(f"{delay_minutes or 0} min delay (+{score:.0f})")
    if missed:
        score += 25.0
        reasons.append("missed an onward connection (+25)")
    if wait_minutes:
        extra = min(wait_minutes / 480.0, 1.0) * 15.0
        score += extra
        reasons.append(f"waits {round(wait_minutes / 60, 1)} h for the next flight (+{extra:.0f})")
    if vulnerable:
        score += 10.0
        reasons.append("special assistance, infant or children (+10)")
    return round(min(score, 100.0), 1), reasons


def flight_severity(delay_minutes: int | None, cancelled: bool) -> dict[str, Any]:
    """Severity of the disruption itself (a passenger with no extra factors) and its label."""
    score, _ = severity(delay_minutes, cancelled, False, None, False)
    label = "minor" if score < 25 else "moderate" if score < 50 else "major" if score < 75 else "severe"
    return {"score": score, "label": label}


def preferences(p: dict[str, Any]) -> tuple[dict[str, float], dict[str, list[str]]]:
    """Proxy preference per reward type (0-1) and the clues that fired. Assumptions, not stated preferences."""
    tier = p.get("loyalty_tier_synthetic")
    freq = str(p.get("travel_frequency_band") or "occasional")
    family = str(p.get("fare_family_synthetic") or "")
    digital = p.get("sales_channel") in DIGITAL_CHANNELS
    has_children = (p.get("children") or 0) + (p.get("infants") or 0) > 0
    member = bool(p.get("is_loyalty_member"))
    prefs: dict[str, float] = {}
    why: dict[str, list[str]] = {k: [] for k in TYPE_LABEL}

    s = 0.3
    if p.get("has_meal"):
        s += 0.4
        why[MEAL].append("bought a meal on the booking")
    if has_children:
        s += 0.2
        why[MEAL].append("travelling with children")
    prefs[MEAL] = min(s, 1.0)

    s = 0.2
    if digital:
        s += 0.25
        why[VOUCHER].append("books online or in the app")
    if family in PRICE_SENSITIVE_FAMILIES:
        s += 0.15
        why[VOUCHER].append(f"{family} fare (price conscious)")
    prefs[VOUCHER] = min(s, 1.0)

    s = 0.15
    if p.get("has_seat"):
        s += 0.45
        why[LOUNGE].append("paid for a seat")
    if family in PREMIUM_FAMILIES:
        s += 0.2
        why[LOUNGE].append("Ultimate fare")
    if freq in HIGH_FREQUENCY:
        s += 0.2
        why[LOUNGE].append("frequent traveller")
    prefs[LOUNGE] = min(s, 1.0)

    if member:
        s = 0.3
        why[MILES].append("loyalty member")
        if freq in REGULAR_OR_BETTER:
            s += 0.3
            why[MILES].append(f"{freq} traveller")
        if tier:
            s += 0.2
            why[MILES].append(f"{tier} tier")
        prefs[MILES] = min(s, 1.0)
    else:
        prefs[MILES] = 0.0

    s = 0.2
    if freq in HIGH_FREQUENCY:
        s += 0.3
        why[TICKET].append("frequent traveller")
    if tier in TOP_TIERS or family in PREMIUM_FAMILIES:
        s += 0.3
        why[TICKET].append("high-value customer")
    if (p.get("pnr_size") or 1) >= 2:
        s += 0.2
        why[TICKET].append("travels with others")
    prefs[TICKET] = min(s, 1.0)
    return prefs, why


def eligible_options(person: Person, rules: RewardRules) -> list[Option]:
    options: list[Option] = []
    if person.disrupted_minutes >= rules.meal_min_minutes:
        options.append(Option(MEAL, TYPE_LABEL[MEAL], rules.meal_aed, "AED 50 airport meal voucher"))
    options += [Option(VOUCHER, TYPE_LABEL[VOUCHER], v, f"AED {v:g} shopping voucher") for v in rules.voucher_aed]
    if person.disrupted_minutes >= rules.lounge_min_minutes:
        options.append(Option(LOUNGE, TYPE_LABEL[LOUNGE], rules.lounge_aed, "Lounge access while waiting"))
    if person.loyalty_member:
        options += [Option(MILES, TYPE_LABEL[MILES], v, f"{m:,} loyalty miles") for m, v in rules.miles]
    if person.severity >= rules.ticket_min_severity:
        options.append(Option(TICKET, TYPE_LABEL[TICKET], rules.ticket_aed, "Free ticket on a future flight"))
    return options


def target_aed(person: Person, rules: RewardRules) -> float:
    return rules.max_target_aed * (person.severity / 100.0) * (0.4 + 0.6 * person.value / 100.0)


def _pref(person: Person, option: Option) -> float:
    """Chance the passenger takes this reward: the trained model if there is one, else the proxy rules."""
    return person.accept.get((option.kind, option.cost), person.prefs.get(option.kind, 0.0))


def _type_scores(person: Person) -> dict[str, float]:
    if not person.accept:
        return person.prefs
    best: dict[str, float] = {}
    for (kind, _), v in person.accept.items():
        best[kind] = max(best.get(kind, 0.0), v)
    return best


def _utility(person: Person, option: Option) -> float:
    return (person.severity / 100.0) * (0.4 + 0.6 * person.value / 100.0) * _pref(person, option) * sqrt(option.cost)


def _chain(person: Person, rules: RewardRules) -> list[tuple[Option, float]]:
    """Options within the target, cheapest first, keeping only those that add utility over every cheaper one."""
    cap = target_aed(person, rules)
    chain: list[tuple[Option, float]] = []
    for o in sorted(eligible_options(person, rules), key=lambda o: (o.cost, o.kind)):
        if o.cost > cap:
            continue
        u = _utility(person, o)
        if u <= 0:
            continue
        if chain and o.cost == chain[-1][0].cost:  # same price: keep the one the passenger prefers
            if u > chain[-1][1]:
                chain[-1] = (o, u)
        elif not chain or u > chain[-1][1]:
            chain.append((o, u))
    return chain


def _why(person: Person, chosen: Option | None) -> list[str]:
    if chosen is None:
        return []
    clues = person.pref_reasons.get(chosen.kind, [])
    if person.accept:
        return [f"predicted acceptance {round(100 * _pref(person, chosen))}%", *clues]
    return clues


def recommend(people: list[Person], budget_aed: float, rules: RewardRules | None = None) -> dict[str, Any]:
    """The plan: one reward (or none) per passenger, total cost within the budget."""
    rules = rules or RewardRules()
    chains = {
        i: _chain(p, rules) for i, p in enumerate(people) if not (p.non_revenue and not rules.non_revenue_gets_reward)
    }
    level = {i: len(c) - 1 for i, c in chains.items()}  # index of the chosen option; -1 = none

    def cost_at(i: int, lv: int) -> float:
        return chains[i][lv][0].cost if lv >= 0 else 0.0

    def util_at(i: int, lv: int) -> float:
        return chains[i][lv][1] if lv >= 0 else 0.0

    ideal = sum(cost_at(i, lv) for i, lv in level.items())
    total = ideal
    downgraded: set[int] = set()
    while total > budget_aed + 1e-9:
        best: tuple[float, int] | None = None
        for i, lv in level.items():
            if lv < 0:
                continue
            saved = cost_at(i, lv) - cost_at(i, lv - 1)
            lost = util_at(i, lv) - util_at(i, lv - 1)
            ratio = lost / saved
            if best is None or ratio < best[0] - 1e-12:
                best = (ratio, i)
        if best is None:
            break
        i = best[1]
        total -= cost_at(i, level[i]) - cost_at(i, level[i] - 1)
        level[i] -= 1
        downgraded.add(i)

    rows: list[dict[str, Any]] = []
    by_type: dict[str, dict[str, float]] = {}
    for i, p in enumerate(people):
        lv = level.get(i, -1)
        chosen = chains[i][lv][0] if i in chains and lv >= 0 else None
        if p.non_revenue and not rules.non_revenue_gets_reward:
            note = "Non-revenue passenger: no goodwill reward."
        elif chosen is None and i in chains and not chains[i]:
            note = "The target for this passenger is below the smallest reward."
        elif chosen is None:
            note = "The budget did not reach this passenger."
        else:
            note = ""
        if chosen:
            slot = by_type.setdefault(chosen.kind, {"passengers": 0, "spend_aed": 0.0})
            slot["passengers"] += 1
            slot["spend_aed"] += chosen.cost
        ranked_prefs = sorted(((v, k) for k, v in _type_scores(p).items() if v > 0), reverse=True)
        rows.append(
            {
                "pnr": p.pnr,
                "customer_key": p.customer_key,
                "passenger_id": p.passenger_id,
                "route": p.route,
                "tier": p.tier,
                "severity": p.severity,
                "severity_reasons": p.severity_reasons,
                "value": p.value,
                "target_aed": round(target_aed(p, rules)),
                "reward": None
                if chosen is None
                else {
                    "type": chosen.kind,
                    "label": chosen.label,
                    "detail": chosen.detail,
                    "cost_aed": chosen.cost,
                    "acceptance": round(_pref(p, chosen), 3),
                },
                "preferred": [{"type": k, "label": TYPE_LABEL[k], "score": round(v, 2)} for v, k in ranked_prefs[:3]],
                "why": _why(p, chosen),
                "downgraded_for_budget": i in downgraded and chosen is not None,
                "note": note,
            }
        )
    rows.sort(key=lambda r: (-(r["reward"]["cost_aed"] if r["reward"] else 0), -r["severity"], r["pnr"]))
    return {
        "budget_aed": round(budget_aed, 2),
        "planned_spend_aed": round(total, 2),
        "left_aed": round(max(budget_aed - total, 0.0), 2),
        "ideal_spend_aed": round(ideal, 2),
        "budget_covers_share": round(min(budget_aed / ideal, 1.0), 3) if ideal else 1.0,
        "passengers": len(people),
        "rewarded": sum(1 for r in rows if r["reward"]),
        "by_type": {
            k: {"passengers": int(v["passengers"]), "spend_aed": round(v["spend_aed"], 2)} for k, v in by_type.items()
        },
        "rows": rows,
    }


def people_for(
    passengers: list[dict[str, Any]],
    scenario: dict[str, Any],
    kind: str,
    delay_minutes: int | None,
    weights: dict[str, float],
    model: Any | None = None,
) -> list[Person]:
    """Build the inputs from the flight's passengers and the scenario result (missed connections, waits)."""
    cancelled = kind == "CANCEL"
    missed = {(c["pnr"], c["customer_key"]) for c in scenario.get("misconnections", [])}
    waits = {
        (r["pnr"], r["customer_key"]): (r.get("care") or {}).get("wait_minutes") for r in scenario.get("passengers", [])
    }
    ranked = priority.rank(passengers, weights, missed, {})
    scores = sorted(x.score for x in ranked)

    def value_of(score: float) -> float:
        """Passenger value 0-100: where the recovery-priority score stands among the flight's passengers."""
        if len(scores) < 2:
            return 50.0
        return round(100.0 * sum(1 for v in scores if v < score) / (len(scores) - 1), 1)

    people: list[Person] = []
    rows: list[dict[str, Any]] = []
    for r in ranked:
        p = r.passenger
        key = (p["pnr"], p["customer_key"])
        wait = waits.get(key)
        vulnerable = p.get("ssr_code") in priority.CARE_SSRS or (p.get("children") or 0) + (p.get("infants") or 0) > 0
        sev, reasons = severity(delay_minutes, cancelled, key in missed, wait, vulnerable)
        disrupted = int(wait) if wait else (delay_minutes or 240)
        prefs, why = preferences(p)
        rows.append(p)
        people.append(
            Person(
                pnr=p["pnr"],
                customer_key=p["customer_key"],
                passenger_id=p.get("passenger_id"),
                route=f"{p['origin']}-{p['destination']}",
                tier=r.tier,
                value=value_of(r.score),
                severity=sev,
                severity_reasons=reasons,
                disrupted_minutes=max(disrupted, delay_minutes or 0),
                loyalty_member=bool(p.get("is_loyalty_member")),
                non_revenue=r.non_revenue,
                prefs=prefs,
                pref_reasons=why,
            )
        )
    if model is not None:  # one batch: every eligible option of every passenger
        pairs = [(i, o) for i, person in enumerate(people) for o in eligible_options(person, RewardRules())]
        probs = model.accept([rows[i] for i, _ in pairs], [(o.kind, o.cost, people[i].severity) for i, o in pairs])
        for (i, o), prob in zip(pairs, probs, strict=True):
            people[i].accept[(o.kind, o.cost)] = float(prob)
    return people
