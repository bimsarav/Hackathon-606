"""Builds docs/delivery/Disruption_Advisor_Methods.pdf (methods, theories, justifications) with ReportLab.

Usage (any Python 3.11+ with reportlab installed): python docs/delivery/tools/make_methods_pdf.py docs/delivery/Disruption_Advisor_Methods.pdf
Not part of the application runtime.
"""

import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

OUT = sys.argv[1]
INK, MUTED, ACCENT, LINE, BAND = (colors.HexColor(c) for c in ("#16202a", "#5a6776", "#0b6e8a", "#d8dee5", "#eef5f7"))

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=15, textColor=ACCENT,
                    spaceBefore=12, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, textColor=INK,
                    spaceBefore=9, spaceAfter=4)
B = ParagraphStyle("B", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.4, leading=13, textColor=INK,
                   alignment=TA_LEFT, spaceAfter=4)
S = ParagraphStyle("S", parent=B, fontSize=8.2, leading=11, textColor=MUTED)
C = ParagraphStyle("C", parent=B, fontSize=8.2, leading=10.5, spaceAfter=0)
CH = ParagraphStyle("CH", parent=C, fontName="Helvetica-Bold", textColor=colors.white)
F = ParagraphStyle("F", parent=B, fontName="Courier", fontSize=8.6, leading=11.5, backColor=BAND,
                   borderPadding=5, leftIndent=6, rightIndent=6, spaceBefore=4, spaceAfter=8)
TITLE = ParagraphStyle("T", parent=H1, fontSize=22, leading=26, textColor=INK, spaceAfter=4)


def p(text: str, style: ParagraphStyle = B) -> Paragraph:
    return Paragraph(text, style)


def bullets(items: list[str]) -> list[Paragraph]:
    return [Paragraph(f"&bull;&nbsp; {i}", ParagraphStyle("li", parent=B, leftIndent=10, firstLineIndent=-8,
                                                            spaceAfter=2)) for i in items]


def table(rows: list[list[str]], widths: list[float]) -> Table:
    data = [[Paragraph(c, CH if r == 0 else C) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BAND]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def footer(canvas, doc) -> None:  # noqa: ANN001
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "Disruption Advisor (UC5) - Methods, theories and justifications - MVP, 20 Nov 2026")
    canvas.drawRightString(192 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


story: list = []
story += [
    p("Disruption Advisor", TITLE),
    p("Methods, theories and justifications (MVP, phase 1)", ParagraphStyle("st", parent=H2, textColor=MUTED, fontSize=13)),
    p("Use case UC5: Flight &amp; Passenger Disruption Management. Version 1.0, 20 November 2026. "
      "Audience: OCC and PCU business owners, solution reviewers and judges.", S),
    Spacer(1, 6),
    p("<b>Labels used.</b> [STD] standard or regulation, [PRACTICE] common airline practice, [ACADEMIC] research, "
      "[ASSUMPTION] our assumption to validate with the airline. Reference numbers like [R4] point to Section 10.", S),
]

story += [p("1. Summary", H1)]
story += bullets([
    "The MVP is a <b>decision-support tool</b>, not an autonomous system: it recommends, a person approves, and every decision "
    "is audited. Operational control stays with the people who legally hold it [STD, R14].",
    "It uses <b>transparent methods</b>: deterministic simulation for delay propagation, rule tables for legality, an "
    "integer-programming solver for seat allocation, an additive scoring model for passenger priority, and a language model "
    "only to <i>word</i> results. No black-box machine-learning model takes part in any MVP decision.",
    "<b>Explainable AI (XAI)</b> is built in by design: every number on screen can be traced to a formula and its inputs "
    "(Section 8). Post-hoc XAI such as SHAP is planned for the phase-2 prediction model, where it is needed.",
    "Gaps in the supplied data were filled with <b>labelled, deterministic synthetic data</b> (Section 3), as instructed by the "
    "user, so that every synthetic value can be replaced by real data without changing the logic.",
])

story += [p("2. Why this approach (choice of techniques)", H1)]
story += [p(
    "Published airline evidence points the same way: the best-documented production systems for disruption recovery use "
    "<b>optimisation with human acceptance</b>, not end-to-end machine learning. Lufthansa Group / SWISS with Google run a "
    "recovery optimiser daily; controllers accepted about 26% of all their changes from it [PRACTICE, R1]. The research "
    "literature models recovery as aircraft, crew and passenger re-planning problems solved with operations research "
    "[ACADEMIC, R2, R3, R4], and hybrids where machine learning only speeds up the optimiser [ACADEMIC, R5]. Generic delay "
    "prediction has the weakest production evidence, which is why it is phase 2, not the MVP.")]
story += [table([
    ["Need (from UC5)", "Technique chosen", "Why not the alternative"],
    ["Impact of a delay over 7 days", "Deterministic propagation along the aircraft rotation", "A learned model would need labelled "
     "cascades we do not have, and its output could not be checked flight by flight."],
    ["Compare recovery actions", "Scenario enumeration (absorb vs same-type swaps) with a cost model", "A full integrated optimiser "
     "needs crew data (not supplied); enumeration is exact for the two approved levers."],
    ["Who gets the limited seats", "Lexicographic tiers + simple additive weighting (MCDA)", "One blended score could let fare value "
     "outrank legal care duties; tiers make that impossible."],
    ["Assign seats, keep families together", "0/1 integer programming solved with OR-Tools CP-SAT", "Greedy assignment can strand a "
     "family or waste seats; CP-SAT returns a proven optimal plan in under a second."],
    ["Explain and communicate", "Grounded generative AI (Claude) over engine facts, with templates as fallback", "Letting the LLM "
     "decide would be unverifiable; it only rewords numbers the engine produced."],
], [42, 58, 72])]

story += [p("3. Generated synthetic data", H1)]
story += [p(
    "The supplied extracts had no loyalty tier, passenger identity beyond the name, special-service codes (SSR), fare-family "
    "mapping, crew data or aircraft list. The user decided (Q4-Q11, Q25, Q30) to fill these gaps with synthetic data built from the "
    "given data plus domain knowledge. All synthetic values are <b>deterministic</b> (md5 hash of the passenger and booking, so "
    "every rebuild gives the same result), <b>labelled</b> in the data (<i>*_synthetic</i> and <i>*_source</i> columns) and "
    "marked with * in the UI. Counts are for the operating window 19-30 Nov 2026.")]
story += [table([
    ["Field", "How it is generated", "Result", "Justification / replace with"],
    ["Customer key", "SHA-256 of normalised first + last name (the only identity available)", "174,723 passengers",
     "Needed to link bookings to travel history. Replace with loyalty or customer ID."],
    ["Travel frequency (real counts)", "Flown segments in the 12 months before 20 Nov 2026, by customer key. Names in more than 60 "
     "bookings a year are flagged 'unknown' (common or placeholder names)", "5,197 frequent travellers who are not loyalty members",
     "UC5 asks to recognise frequent travellers without membership. Real counts, synthetic identity."],
    ["Loyalty tier", "Members only: 24+ segments Platinum, 12+ Gold, 6+ Silver, else Blue", "Blue 30,845 · Silver 5,312 · Gold 3,611 · "
     "Platinum 5,038 · non-members 129,917", "Tier names and thresholds are assumptions [ASSUMPTION]. Replace with the airline's tier file."],
    ["Fare family", "Booking classes E9...E45 ordered by average fare; cheapest 50% of passengers Basic, next 35% Value, top 15% "
     "Ultimate; other codes 'Other'", "Basic 109,800 · Value 112,732 · Ultimate 29,362 · Other 46,433 segments",
     "Fare value and family feed the priority score. Replace with the booking-class to fare-family table."],
    ["Revenue / non-revenue", "Codes whose active bookings are zero-fare (VI, DU, DT, Z, DUMKT, GD, DUFAM) = staff / ID travel",
     "1,024 non-revenue segments", "Data-derived pattern [ASSUMPTION on the code meaning]. Confirm with the airline."],
    ["Infant link (INFT)", "Each infant linked to an adult in the same booking", "3,344 (from data)", "Data-derived. Infants sit on "
     "an adult's lap: no seat, travel with that adult."],
    ["Special assistance SSR", "Deterministic draw for adults: WCHR 0.60%, WCHS 0.15%, WCHC 0.05%, BLND 0.03%, DEAF 0.03%, MEDA "
     "0.05%, PREG 0.10%", "WCHR 1,709 · WCHS 396 · PREG 294 · WCHC 138 · MEDA 115 · DEAF 96 · BLND 74",
     "Rates are assumptions [ASSUMPTION] so that the care tier can be demonstrated. Replace with SSR data from the PSS/DCS."],
    ["Aircraft registry and seats", "Model from exact inventory matches; seats = smallest layout (174 A320 / 215 A321) that fits "
     "the most passengers the aircraft ever carried (12 infants allowed)", "44 inventory-exact, 11 A321 inferred, 55 assumed A320/174",
     "Needed for same-type swaps and capacity. Replace with the registration to type file (PO said it may be supplied)."],
    ["Seat capacity per flight", "Inventory allocation incl. curtail/oversell where present (only 6 window flights), else the "
     "aircraft seats above; available = capacity - booked (never below 0)", "1,830 flights inventory-exact, 426 inferred, 2,390 assumed",
     "PO: capacity comes from inventory allocation; mismatches must not break the process."],
    ["Airport time zones", "Public dataset (mwgg/Airports, MIT); 4 stations added by hand (FRU, DBS, RYD, DMF)", "142 stations",
     "User decision Q22. Bus points' time zones are assumptions."],
], [27, 55, 40, 50])]

story += [PageBreak(), p("4. Data foundations", H1)]
story += [p("4.1 Columnar storage and predicate push-down", H2), p(
    "All extracts are converted once to typed Apache Parquet (columnar, zstd-compressed) and queried with DuckDB. A query reads "
    "only the columns it needs, and filters such as the date window are pushed down to the file read, so 27.9 million booking rows "
    "(642 MB) are scanned in seconds on a normal server. Malformed rows are counted and skipped instead of stopping the run "
    "(2 booking lines, 1 inventory line), as the product owner required.")]
story += [p("4.2 Time and distance", H2), p(
    "All logic runs in UTC; local times come from IANA time zones. Great-circle distance (haversine formula on a sphere of radius "
    "6,371 km) is used for EU261 distance bands:")]
story += [p("d = 2R &middot; asin( sqrt( sin<super>2</super>(&Delta;&phi;/2) + cos &phi;<sub>1</sub> cos &phi;<sub>2</sub> "
            "sin<super>2</super>(&Delta;&lambda;/2) ) )", F)]

story += [p("5. Network impact: reactionary delay propagation", H1)]
story += [p(
    "<b>Theory.</b> An aircraft flies a chain of legs (its rotation). A late arrival delays the next departure unless the planned "
    "ground time contains slack. This 'reactionary' delay is the largest delay category in Europe: 46% of delay minutes in 2023 "
    "[STD/PRACTICE, R6]; IATA codes 91-96 classify it [STD, R7]. In the supplied G9 punctuality data reactionary codes account for "
    "about 76% of coded delay minutes, so modelling the rotation is the core of impact assessment.")]
story += [p("For legs i = 1..n of one aircraft, with scheduled departure STD<sub>i</sub>, block time b<sub>i</sub> and minimum "
            "turn time T (default 40 min, configurable):")]
story += [p("ETD<sub>1</sub> = STD<sub>1</sub> + delay<br/>ETA<sub>i</sub> = ETD<sub>i</sub> + b<sub>i</sub><br/>"
            "ETD<sub>i+1</sub> = max( STD<sub>i+1</sub> , ETA<sub>i</sub> + T )<br/>"
            "knock-on delay<sub>i</sub> = ETD<sub>i</sub> - STD<sub>i</sub>", F)]
story += [p("<b>Justification.</b> The model is exact for the given schedule and turn-time rule, fast (milliseconds for a 7-day "
            "horizon) and checkable leg by leg by a controller. It does not model ATC slots or crew rest; those are listed limits.")]

story += [p("6. Recovery options and their cost", H1), p("6.1 Same-type aircraft swap", H2), p(
    "<b>Theory.</b> Aircraft recovery literature uses tail swaps, delays, cancellations and ferry flights as recovery levers "
    "[ACADEMIC, R2, R3]. The MVP implements the two levers the product owner approved first: absorb the delay, or swap with an "
    "aircraft of the same seat count (equipment change is phase 4). A swap exchanges the <i>remaining rotations</i> of the late "
    "aircraft and a candidate at the station where the late aircraft lands, so both rotations stay continuous. Candidates are "
    "aircraft departing that station within 3 hours of the takeover; a candidate is feasible only if it is on the ground at that "
    "station at that time. Each feasible swap is propagated with the formulas of Section 5 for both aircraft.")]
story += [p("6.2 Connection feasibility", H2), p(
    "A connection is the same passenger in the same booking arriving at a station and leaving it 15 minutes to 20 hours later "
    "(user decision Q8). It is missed when the new connection time is below the Minimum Connecting Time: the hub table for that "
    "origin/hub/destination (50-55 min at SHJ) or a 45-minute default [STD, R8]. Assessing impact per passenger journey matters "
    "because about half of passenger delay minutes come from cancellations and missed connections [ACADEMIC, R9].")]
story += [p("6.3 Cost model and ranking", H2), p(
    "Each option is costed with assumed, configurable rates (user decision Q15) and the cheapest is recommended; ties are broken by "
    "fewer missed connections. Delay minutes, passengers affected and missed connections are shown beside the cost so the trade-off "
    "stays visible (contrastive comparison).")]
story += [p("cost = 400 AED x delay minutes<br/>"
            "     + 50 AED x passengers on legs delayed &gt;= 120 min      (meal care)<br/>"
            "     + 4 AED/EUR x EU261 compensation                       (legs departing EU/EEA/CH, delay &gt;= 180 min)<br/>"
            "     + 75 AED x missed connections                         (25 handling + 50 meal)", F)]
story += [p("EU261 compensation by distance: up to 1,500 km EUR 250; 1,500-3,500 km EUR 400; over 3,500 km EUR 600 "
            "(intra-EU over 1,500 km: EUR 400) [STD, R10].")]
story += [KeepTogether([p("<b>Worked example (real data).</b> G9519 DAC-SHJ delayed 150 min, turn at SHJ only 55 min:", B), table([
    ["Option", "Delay min", "Legs", "Missed conn.", "Cost (AED)"],
    ["Swap: A6-ARI takes over G9294 (recommended)", "150", "1", "33", "70,875 = 60,000 + 8,400 + 0 + 2,475"],
    ["Swap: A6-ANO", "150", "1", "33", "70,875 (equal fallback)"],
    ["Swap: A6-AQG", "300", "3", "55", "132,525"],
    ["Absorb the delay", "480", "5", "90", "222,600"],
], [62, 20, 13, 22, 55])])]

story += [PageBreak(), p("7. Passenger prioritisation and re-accommodation", H1), p("7.1 Lexicographic tiers", H2), p(
    "<b>Theory.</b> Multi-criteria decision analysis distinguishes <i>lexicographic</i> ordering (a higher criterion always wins) "
    "from <i>compensatory</i> weighting (criteria trade off). Passenger-rights law sets non-negotiable priorities: EU/UK261 Art. 11 "
    "gives priority to persons with reduced mobility and unaccompanied children [STD, R11]; Canada's APPR s.15(4) fixes an order "
    "for denied boarding [STD, R12]; Brazil's ANAC Res. 400 Art. 28 prioritises passengers needing assistance [STD, R13]. "
    "Commercial value must therefore never outrank these. The MVP orders passengers lexicographically:")]
story += bullets([
    "<b>Tier 1, mandated care:</b> WCHR/WCHS/WCHC, BLND, DEAF, MEDA, PREG, bookings with an infant. (Unaccompanied minors "
    "are out of scope for the MVP; future enhancement.)",
    "<b>Tier 2, urgency:</b> an onward connection, or a multi-sector journey within 24 hours.",
    "<b>Tier 3:</b> everyone else. <b>Non-revenue</b> (staff/ID) passengers come after all revenue passengers.",
])
story += [p("7.2 Weighted score inside a tier (simple additive weighting)", H2), p(
    "Within a tier, a compensatory score orders passengers. Each attribute is normalised to [0, 1] and multiplied by a "
    "user-adjustable weight w<sub>k</sub> (defaults: loyalty 20, frequency 15, fare value 20, ancillaries 10, journey 20, family/group 15):")]
story += [p("score = 100 x &Sigma;<sub>k</sub> w<sub>k</sub> v<sub>k</sub> / &Sigma;<sub>k</sub> w<sub>k</sub><br/>"
            "contribution<sub>k</sub> = 100 x w<sub>k</sub> v<sub>k</sub> / &Sigma; w     (shown per passenger)<br/>"
            "v_loyalty: none 0, Blue .25, Silver .5, Gold .75, Platinum 1<br/>"
            "v_frequency: occasional .2, regular .6, frequent 1, unknown .3<br/>"
            "v_fare = .7 x percentile rank of fare + .3 x family value (Basic .2, Value .5, Ultimate 1)<br/>"
            "v_ancillaries = min(ancillaries / 150, 1);  v_journey = min(.6 x onward + .2 x extra sectors, 1)<br/>"
            "v_booking = 1 family with child/infant, .5 group of 5+, else 0", F)]
story += [p("<b>Justification.</b> Additive weighting is transparent, monotonic and easy to tune in a what-if; percentile ranks "
            "make fares comparable across routes. UC5 asks for 'configurable weightages' that 'explain why a passenger is "
            "prioritised' and that 'respect passenger rights independently of commercial scores': the tier + weight design "
            "meets all three. Published US practice shows commercial ranking is common (e.g. by fare and status, 14 CFR 250.3) "
            "but must avoid unjust discrimination [STD, R15].")]
story += [p("7.3 Seat assignment by integer programming (OR-Tools CP-SAT)", H2), p(
    "<b>Theory.</b> Re-accommodation with limited seats is a 0/1 assignment problem with capacity constraints (a multiple-knapsack "
    "/ generalised assignment structure). Each booking group g (all its seated passengers, so families stay together) can go to at "
    "most one alternative flight f within 24 hours on the same route:")]
story += [p("maximise   &Sigma;<sub>g,f</sub> x<sub>g,f</sub> (V<sub>g</sub> - 2 x hours late<sub>f</sub> x |g| - "
            "2,500 x passengers losing their onward connection)<br/>"
            "subject to  &Sigma;<sub>f</sub> x<sub>g,f</sub> &lt;= 1      for every group g<br/>"
            "            &Sigma;<sub>g</sub> |g| x<sub>g,f</sub> &lt;= free seats<sub>f</sub>   for every flight f<br/>"
            "            x<sub>g,f</sub> in {0, 1}<br/>"
            "V<sub>g</sub> = &Sigma; over members of (100,000 tier 1 | 5,000 tier 2 | 200 tier 3) + score; non-revenue = 1", F)]
story += [p("The tier values are far apart, so the solver reproduces the lexicographic order (a tier never loses seats to a lower "
            "tier for normal group sizes), while the score and lateness decide inside a tier. CP-SAT combines constraint "
            "propagation, SAT search and linear relaxations and proves optimality; on real cases (147 passengers, 60 seats) it "
            "returns OPTIMAL in under a second. A group larger than any free block is split and reported as split. Passengers "
            "left without a seat are offered next day with hotel and meals, or a refund.")]

story += [p("7.4 Care while waiting", H2), p(
    "<b>Theory.</b> EU261 Art. 9 sets care 'in relation to the waiting time': meals and refreshments, and hotel accommodation "
    "plus transport when a stay of one or more nights is needed [STD, R10]. It applies only to EU/EEA/CH departures, so for other "
    "stations the same structure is used as configurable airline policy [ASSUMPTION]. Rules: under 2 h no care; 2 h or more one "
    "meal voucher per 4 h (at most 4); 8 h or more, or a wait overlapping the local night (01:00-05:00) by 2 h, adds a hotel room "
    "and transport; no seat within 24 h counts as next day. From 5 h of waiting, and for anyone without a seat, the passenger "
    "may choose a refund with a free return to origin or a date change. Flags: transfer passengers who need a hotel (transit "
    "visa or airside hotel), special assistance to re-book, pregnancy fit-to-fly, infant supplies. <b>Justification.</b> A "
    "rebooking 18-19 h later is only acceptable with overnight care; costing it (hotel AED 350 + transport 2 x AED 60 + meals) "
    "makes long waits visible in the plan instead of hiding them behind a single meal voucher.")]
story += [p("8. Explainable AI (XAI): what is used", H1)]
story += [p(
    "<b>Direct answer:</b> no post-hoc XAI library (SHAP, LIME) is used in the MVP, because no black-box model makes a decision. "
    "Instead the MVP is <b>explainable by design</b> ('glass-box'): every output is produced by a formula or rule whose inputs are "
    "shown. This is the strongest form of explanation, because it is exact rather than approximated. It also matters legally: an "
    "automated score that decides who is stranded can count as an automated decision under GDPR Art. 22 (CJEU SCHUFA, C-634/21) "
    "[STD, R16], so explanations and human review are required.")]
story += [table([
    ["XAI technique", "Where it appears", "What the user sees"],
    ["Exact feature attribution (additive model)", "Passenger score", "Points per attribute (e.g. Loyalty +15, Fare +12). For an "
     "additive model these equal its Shapley values exactly."],
    ["Rule-based (symbolic) explanation", "Priority tier", "The rule that fired: 'Tier 1 (Mandated care: WCHR)'."],
    ["Contrastive explanation", "Recovery options table", "Why option A rather than B: delay, legs, missed connections and cost side "
     "by side."],
    ["Decomposition", "Option cost", "Cost split into aircraft delay, passenger care, EU261 and misconnect handling."],
    ["Constraint-based explanation", "Rebooking plan", "Why a passenger has or lacks a seat: free seats, group kept together or "
     "split, onward connection kept or lost."],
    ["What-if (counterfactual) analysis", "Weights panel", "Change a weight, re-run, and see who moves."],
    ["Grounded natural-language explanation", "'Why this recommendation' box", "Claude rewrites the engine's numbers into prose; it "
     "receives only those facts, so it cannot invent a different decision."],
], [50, 38, 84])]
story += [p("Phase 2 adds a LightGBM delay-risk model; there post-hoc XAI is needed and SHAP (TreeExplainer) will show the "
            "drivers of each prediction.", S)]

story += [p("9. Generative AI and human oversight", H1)]
story += bullets([
    "<b>Grounded generation:</b> the model (claude-opus-5-5, low effort) gets a fixed system instruction ('use only the facts given') "
    "and a JSON of engine facts. It never chooses an option or a passenger.",
    "<b>Data minimisation:</b> no names, booking references or contact details are sent; only flight numbers, stations, times, counts "
    "and reasons (GDPR principle; data treated as real per user decision Q3).",
    "<b>Resilience:</b> server-side refusal fallback; on any API error, timeout or refusal a deterministic template is used, so the "
    "tool works without the AI.",
    "<b>Human in the loop:</b> operational control of flights is a legal responsibility of the captain and dispatcher or the "
    "operator's designated staff [STD, R14]. The tool recommends; approve/reject decisions are recorded with user, role and time.",
])

story += [p("10. Limitations and what must be validated", H1)]
story += bullets([
    "Costs, the 40-minute turn time, the 45-minute default MCT and the SSR rates are assumptions (configurable) [ASSUMPTION].",
    "Crew duty limits are not checked (no crew data): crew control must confirm every swap.",
    "Out of scope (future enhancements): unaccompanied minors, partner and other carriers.",
    "Only two recovery levers (absorb, same-type swap); cancellation/consolidation and equipment change come in phases 3-4.",
    "Seat capacity is inferred for most window flights because the inventory extract covers only 6 of them.",
    "Passenger identity is name-based; travel frequency for common names is unreliable and capped.",
    "EU261 is estimated (no extraordinary-circumstances or rerouting reductions); other regimes use generic care rules.",
])

story += [p("11. References", H1)]
refs = [
    "R1 Davies et al., Decision Support for Schedule Recovery at Lufthansa Group Airlines, INFORMS J. Applied Analytics 56(1), 2026.",
    "R2 Kohl, Larsen, Larsen, Ross, Tiourine, Airline disruption management - perspectives, experiences and outlook, J. Air "
    "Transport Management 13(3):149-162, 2007.",
    "R3 Petersen, Solveling, Clarke, Johnson, Shebalov, An optimization approach to airline integrated recovery, Transportation "
    "Science 46(4):482-500, 2012.",
    "R4 Bratu, Barnhart, Flight operations recovery: new approaches considering passenger recovery, J. Scheduling 9(3):279-298, 2006.",
    "R5 Hizir, Barnhart, Vaze, Large-scale airline crew recovery using mixed-integer optimization and supervised machine learning, "
    "Transportation Science 60(2), 2026.",
    "R6 EUROCONTROL, CODA Digest Annual Report 2023 (Dec 2024).",
    "R7 EUROCONTROL PRU / ANS Performance, IATA delay codes (definition page).",
    "R8 IATA, SSIM Chapter 8 - Minimum Connecting Time standards (2021).",
    "R9 Barnhart, Fearing, Vaze, Modeling passenger travel and delays in the National Air Transportation System, Operations "
    "Research 62(3):580-601, 2014.",
    "R10 Regulation (EC) No 261/2004 (EU261), Art. 7; revision Reg. (EU) 2026/2202 applies mainly from 23 Oct 2027.",
    "R11 Regulation (EC) No 261/2004, Art. 11 (UK retained text, legislation.gov.uk).",
    "R12 Canada, Air Passenger Protection Regulations SOR/2019-150, s.15(4).",
    "R13 Brazil, ANAC Resolution 400/2016, Art. 28.",
    "R14 FAA AC 120-101 CHG 1, Part 121 Air Carrier Operational Control (2016).",
    "R15 14 CFR Part 250 (oversales; boarding priority rules), §250.3.",
    "R16 CJEU C-634/21 SCHUFA Holding (Scoring), 7 Dec 2023; GDPR Art. 22.",
    "Tools: Google OR-Tools CP-SAT 9.15; DuckDB 2.0; Apache Parquet; Anthropic Claude API (claude-opus-5-5).",
]
story += [p(r, S) for r in refs]
story += [Spacer(1, 6), p("The full source list with URLs and access dates is kept in the team's airline knowledge base "
                          "(source registry).", S)]

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                        title="Disruption Advisor - Methods, theories and justifications", author="Disruption Advisor team")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("written", OUT)
