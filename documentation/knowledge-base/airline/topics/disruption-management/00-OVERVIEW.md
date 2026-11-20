# Flight & Passenger Disruption Management — Topic Overview (MASTER_PROMPT §15.7)

> **Question:** How can AI help an airline predict, assess and minimise the impact of flight disruptions on its network and passengers, while prioritising passenger recovery intelligently?
> **Status:** first research pass, 2026-11-20. Five deep-dive notes; 261 sources (`../../SOURCES.md`); 98 glossary entries (`../../GLOSSARY.md`).
> This overview synthesises the notes and follows the 14 sections of §15.8. Detail, evidence and every source ID live in the notes. Labels: `[STD]` standard/regulation · `[PRACTICE]` common practice · `[SPECIFIC]` one airline or vendor · `[ACADEMIC]` research · `[AI-OPP]` potential AI improvement · `[VALIDATE]` to confirm.

| Note | Scope (§15.7.x) | Sources |
|---|---|---|
| [01-disruption-prediction.md](01-disruption-prediction.md) | 7.1 delay, cancellation, technical, weather, ATFM, crew and rotation risk | S-P01…56 |
| [02-network-impact-and-recovery.md](02-network-impact-and-recovery.md) | 7.2 propagation, crew legality, airport constraints · 7.5 recovery levers and optimisation, meltdown case studies | S-N01…55 |
| [03-passenger-impact.md](03-passenger-impact.md) | 7.3 PSS/PNR/tickets/EMDs, MCT, inventory, IATA re-accommodation rules, special needs, metrics | S-X01…57 |
| [04-passenger-prioritization-and-rights.md](04-passenger-prioritization-and-rights.md) | 7.4 priority practice, passenger-rights regimes, fairness and privacy | S-R01…53 |
| [05-occ-pcu-workflows-and-systems.md](05-occ-pcu-workflows-and-systems.md) | 7.6 OCC/PCU teams, decision authority, IROPS workflow, systems and message flows, vendors | S-O01…41 |

---

## 1. Executive Summary

- **Most disruption is propagation, not the first event.** In Europe, reactionary (knock-on) delay is the largest delay category: 46% of delay minutes, 8.1 min per flight in 2023 [S-N01]. The draft 2024 digest gives 46% / 8.0 min [S-P02, VALIDATE], and September 2026 gives 7.1 of 15.0 min [S-P01]. For passengers, about half of delay minutes come from cancellations and missed connections, which are rare at flight level [S-X40–S-X42]. **Impact must therefore be assessed per network and per passenger journey, not per flight.** `[STD]` `[ACADEMIC]`
- **The proven value of AI sits in three places:**
  - predictive maintenance (Delta, easyJet/Skywise) [S-P25][S-P27];
  - optimisation-based recovery with a human approving each change (Lufthansa Group/Google OPSD at SWISS: 26% of controller changes come from the solver, CHF 8.5M saved) [S-N31];
  - automated passenger re-accommodation (Air Canada and SWISS with Amadeus, Sabre) [S-X12][S-X13][S-X17].
  These figures are vendor- or airline-reported. `[SPECIFIC]`
- **Generic delay prediction is the least proven layer.** No audited production delay-probability model at a named airline was found. Published accuracy depends on the horizon and cannot be compared across studies [S-P31][S-P36][S-P40]. Once a CTOT/EDCT or ground stop is issued, the delay is largely known. AI earns its value by **anticipating** these and turning them into downstream impact before the decision deadline. `[ACADEMIC]` `[AI-OPP]`
- **Recovery decisions are optimisation problems under hard rules.** The hard rules include crew legality (FAA Part 117, EASA ORO.FTL), curfews and slots, IATA re-accommodation rules (Res 735d, INVOL reissue) and passenger-rights law. Operations research beats pure ML for the decision itself. The strongest research results are **hybrids**: ML shrinks the optimisation model, or reinforcement learning guides the search [S-N33][S-N34]. Pure RL is research-only. `[STD]` `[ACADEMIC]`
- **The binding constraint in real meltdowns was crew tracking and data, not aircraft.** This held for Southwest in December 2022 (US$140M DOT penalty) and Delta in July 2024 (about US$550M cost) [S-N02][S-N08][S-N09]. At OPSD, data integration took about 20 developers over four years, against 5 on the solvers [S-N31]. `[SPECIFIC]`
- **Passenger prioritisation must be lexicographic.** The tiers are, in order: legal and safety feasibility; legally mandated groups (EU/UK261 Art. 11, Canada APPR s.15(4), Brazil ANAC Res. 400 Art. 28); operational urgency; then a commercial or wellbeing score **only as a tie-breaker** [S-R03][S-R24][S-R31]. US rules permit ranking by fare and status (14 CFR 250.3) [S-R11]. EU261 was revised as Reg. (EU) 2026/2202, applying mainly from 23 Oct 2027 [S-R05][S-R06, VALIDATE final text]. GDPR Art. 9 and Art. 22 (SCHUFA) make health data and automated stranding decisions high-risk [S-R38][S-R39]. `[STD]` `[AI-OPP]`
- **Humans keep legal authority.** Dispatch release, delay, cancellation for safety, and diversion belong to the PIC and dispatcher in the US, or to the OM-designated authority and the commander in the EU. Airworthiness belongs to maintenance [S-O01][S-O02][S-O03]. In practice, AI is decision support with human acceptance. GenAI in production is mostly passenger messaging (United) [S-O21][S-O22]. `[STD]` `[SPECIFIC]`

## 2. Airline Domain Fundamentals

- **Disruption (IROPS)** is any deviation from the planned schedule: weather, ATC/ATFM, technical, crew, IT or security. It is managed on two time scales:
  - **pre-tactical**, from D-1 to hours before (pre-cancellations, spares, reserve crew);
  - **tactical/day-of**, in minutes (delays, swaps, cancellations, rebooking) [01 §3][02 §3].
- **Three coupled resources** must be re-planned: aircraft (tail rotations, maintenance windows), crew (pairings, duty limits, reserves) and passengers and bags (itineraries, connections, inventory). Industry practice is still largely sequential: aircraft first, then crew, then passengers. The literature shows integrated recovery is better [02 §1][05 §1]. `[PRACTICE]` `[ACADEMIC]`
- **External authorities control part of the problem.** EUROCONTROL Network Manager and the FAA ATCSCC allocate slots and programs (CTOT, GDP/EDCT, ground stops). Airports run A-CDM (TOBT/TSAT). The airline can request but not decide [01 §5][05 §3]. `[STD]`
- **Business models differ.**
  - Hub carriers protect banks of connections; misconnects dominate passenger impact.
  - LCC point-to-point carriers have few connections but high utilisation and tight turns, so rotation propagation and crew dominate.
  - Regional and capacity-purchase operators split authority with the mainline.
  - [02 §8][05 §9]. `[PRACTICE]`

## 3. Business Processes and Operational Workflows

The end-to-end IROPS flow, with its diagram in [05 §4], has six steps:
1. **Detection:** MVT/ACARS/A-CDM events, ATFM regulations, MCC defects, crew check-in gaps, and forecasts [01 §4][05 §5].
2. **Assessment:** downstream flights by tail and crew, plus passenger journeys at risk.
3. **Recovery options:** retime, swap, consolidate, cancel, ferry, wet lease, reserve or deadhead crew.
4. **Decision** by the controllers and duty manager.
5. **Passenger re-accommodation** (batch, then agents, then self-service) and notification. US 14 CFR 259.8 requires notice within 30 minutes [S-O12].
6. **Post-ops review,** including delay-code allocation [02 §3][03 §3][05 §4].

Three decisions are worth separating:
- **Schedule change vs IROPS.** IATA Res 735d covers changes arising within one day of departure. Earlier changes are planned schedule changes under RP 1735, which uses a different workflow [S-X01]. `[STD]`
- **Hold vs rebook.** Holding an outbound flight for connecting passengers trades misconnects against onward delay. United ConnectionSaver is a production example [S-P33][03 §3.3]. `[SPECIFIC]`
- **Timing.** A recommendation is useful only if it arrives before the decision deadline: "we cannot rebook passengers on a flight departing in 30 minutes if making that decision requires 45 minutes" [S-N31]. `[PRACTICE]`

## 4. Industry Terminology and Definitions

See `../../GLOSSARY.md`, which merges the terminology tables of all notes, with sources. Core terms: IROPS, primary vs reactionary delay, IATA delay codes (AHM 730/731 → 732; 91–96 reactionary), CTOT/EDCT/GDP, A-CDM/TOBT, OCC/IOC/SOCC/HCC, PCU, operational control, FDP, MCT (SSIM Ch. 8), PNR, SSR, EMD-A/S, INVOL reissue, FIM, Res 735d, NDC/ONE Order, APPR, DBC.

## 5. Stakeholders and Responsibilities

The full table is in [05 §3]: team, information needed, decisions, horizon, and human or legal authority. In summary:
- The **duty manager** arbitrates.
- **Dispatch/FOO** decides flight plan, fuel and release, under legal authority.
- **Network/movement control** decides delays, swaps and cancellations.
- **Crew control** decides reassignments within legality.
- **Maintenance control** decides deferral and airworthiness, under legal authority.
- **Hub/airport control** decides TOBT, gates and turnaround recovery.
- **PCU / passenger services** decides re-protection, holds for connections and care.
- **Customer service** carries out rebooking, refunds and care.
- **Customer communications** owns passenger messages.
- **Revenue management** releases inventory for protection; its role is not well documented [VALIDATE].
- **ATFM liaison** handles slot swaps and CDM.

The FAA expects commercial functions in a combined control centre to be separated from operational control [S-O02]. `[STD]`

## 6. Systems and Technology Ecosystem

The system map and data-flow diagram are in [05 §5]. It covers operations control (e.g. Lufthansa Systems NetLine, IBS iFlight, CAE, which acquired Sabre AirCentre in 2022), flight planning (Lido, Jeppesen, sold to Thoma Bravo in 2025), crew management, M&E, PSS/DCS (Amadeus Altéa, Sabre, Navitaire, owned by Amadeus since 2016), revenue management, airport and A-CDM, and distribution (GDS/NDC) [S-O29–S-O32][S-X22]. `[SPECIFIC]`
- **Integration** still relies largely on IATA **Type B** messaging (about 188M messages a day; no guaranteed order; no encryption) and MVT (AHM 780). The modern layer is AIDX/APIs, EUROCONTROL NM B2B and A-CDM events [S-O08][S-O09][S-O06][S-O07]. Any AI layer must handle late, duplicate and out-of-order events. `[STD]` `[PRACTICE]`
- **Re-accommodation products** in production: Amadeus Passenger Recovery and Self Re-accommodation, and Sabre IROPS Reaccommodation [S-X11–S-X17]. No Navitaire equivalent was found [VALIDATE].

## 7. Data Requirements and Data Relationships

| Domain | Key data | Typical origin | Freshness | Standard / format | Note |
|---|---|---|---|---|---|
| Flight movements | Scheduled/estimated/actual times, delay codes | OCC, ACARS, MVT | Real time | AHM 780 MVT, AHM 730–732, AIDX | 01 §4, 05 §5 |
| ATM | Regulations, CTOT/EDCT, GDP/GS | EUROCONTROL NM, FAA SWIM/ATCSCC | Real time | NM B2B, A-CDM DPI, SWIM | 01 §4 |
| Weather | METAR/TAF/SIGMET, convective forecasts | Met services | 30 min to 6 h | ICAO Annex 3 / IWXXM [VALIDATE] | 01 §4 |
| Aircraft | Rotations, tail status, MEL/defects, health data | OCC, M&E, OEM platforms (Skywise etc.) | Real time to daily | vendor-specific | 01 §6, 02 §4 |
| Crew | Rosters, check-in, legality counters, reserves | Crew management system | Real time | vendor-specific; FTL rules | 02 §4–5 |
| Passengers | PNR → passengers → segments → tickets/coupons → EMDs/SSRs; connections | PSS (reservations, inventory, DCS) | Real time | AIRIMP, SSIM Ch. 8 (MCT), Res 725 (EMD), NDC/ONE Order | 03 §4 |
| Inventory | Availability by flight/class, over-authorisation, partner availability | PSS inventory, interline agreements | Real time | AIRIMP "NI", bilateral agreements | 03 §5.3 |
| Commercial | Fare paid, tier, CLV, corporate contracts | PSS, loyalty, CRM | Daily | internal | 04 §4 |
| Sensitive | PRM/medical/pregnancy SSRs, minors | PSS | Per booking | GDPR special category | 04 §4 |
| Cost | Delay cost per minute, compensation exposure, hotels, crew overtime | Finance, rules engine | Periodic | internal [VALIDATE] | 02 §9 |

**Key relationships:**
- **Tail rotation:** delay propagates flight to flight through the aircraft.
- **Crew pairing:** delay propagates through crew, often across fleets.
- **Passenger journey:** the PNR crosses flights through connections, with MCT legality as a hard rule and real connection probability as a separate prediction.
- **Ticket coupons and EMDs:** these determine what can be reissued involuntarily and which ancillaries must be re-associated or refunded [S-X01].

## 8. Business Rules and Operational Constraints

These are hard constraints: they define what is feasible and are never traded off against cost.
- **Safety and legal authority** (PIC, dispatcher, maintenance) [05 §3].
- **Crew duty and rest:** Part 117 FDP 9–14 h, 10 h rest; EASA FDP 13:00 for 1–2 sectors, minus 30 min per extra sector [S-N12–S-N18].
- **Curfews, slots and ATFM** [02 §5].
- **MCT legality** [S-X02].
- **IATA re-accommodation and INVOL rules** [S-X01].
- **Passenger-rights regimes:** EU/UK261, Reg. 2026/2202 from 2027, US 14 CFR 250/259/260, Montreal Art. 19, Canada APPR, India DGCA CAR, Brazil ANAC 400, Gulf rules. The comparison table is in [04 §5]. `[STD]`

Soft and commercial rules come from airline policy and vary by airline:
- priority orders in conditions of carriage (Delta Rule 21 vs Alaska) [S-R40][S-R41];
- hold-for-connection limits, cost thresholds, and approval delegation [05 §10];
- union contracts on reassignment and reserve call-out [02 §9]. `[SPECIFIC]` `[VALIDATE]`

## 9. Industry Practices and Real-World Case Studies

- **Lufthansa Group / SWISS + Google OPSD** (2019–2026, INFORMS Edelman): integrated aircraft, crew and passenger optimisation, human-accepted [S-N31][S-O18].
- **American Airlines HEAT** [S-N47][S-O23].
- **Alaska Flyways:** the dispatcher accepts or rejects [S-O24][S-O25].
- **Lufthansa Systems aiOCC:** reinforcement learning; the decision stays with the controller [S-O20].
- **Air Canada and SWISS with Amadeus Passenger Recovery** [S-X12][S-X13]; **Sabre IROPS Reaccommodation** [S-X17].
- **United:** self-service rebooking (2023) and GenAI disruption messaging [S-X37][S-O21].
- **Predictive maintenance:** Delta [S-P27]; easyJet/Skywise [S-P25].
- **Failures:**
  - Southwest, December 2022: about 16,700–16,900 cancellations, US$140M penalty, crew tracking failure [S-N02–S-N04].
  - Delta, July 2024 (CrowdStrike): more than 7,000 cancellations, about US$550M cost [S-N08][S-N09].
  - Both show that the recovery capacity of crew systems and data, not the algorithms, decides whether a disruption becomes a meltdown.
- **EUROCONTROL:** a better first wave led to all-day improvement in 2025 (0.9 min/flight bought 2.8 min/flight over the day) [S-P03].

## 10. AI and Technology Opportunities

| Opportunity | Method | Evidence today | Right tool? |
|---|---|---|---|
| Early warning of disruption (D-1 to H-3) | Gradient boosting / probabilistic models on schedule, weather, ATFM and rotation features | Research and vendor claims; D-1 ATFM delay prediction [S-P39] | ML, but only if the lead time beats the decision deadline |
| Reactionary-impact projection | Graph propagation over tail and crew links; simulation | Research; codes 91–96 provide labels [S-N01] | Deterministic propagation first, ML for uncertainty |
| Predictive maintenance | OEM health data + ML | **Production** (Delta, easyJet) [S-P25][S-P27] | Proven |
| Integrated recovery | MIP / column generation / LNS; ML-shrunk MIP; RL-guided search | **Production** (OPSD); hybrids in research [S-N31][S-N33][S-N34] | Optimisation, with ML as an accelerator |
| Per-passenger connection risk | Probabilistic models beyond static MCT | Research plus a Heathrow prototype [S-X43][S-X44] | ML |
| Passenger re-accommodation | Rules + optimisation; choice and acceptance prediction for self-service | **Production** (Amadeus, Sabre) [S-X12][S-X17] | Rules + optimisation; ML for acceptance |
| Prioritisation | Lexicographic tiers + configurable tie-break score + explanation | Vendors offer value-based rebooking [S-R43][S-R46]; fairness evidence is thin | Rules first; ML only inside a tier |
| Passenger and agent communication | LLM drafting with human or template guardrails | **Production** at United [S-O21][S-O22] | GenAI, with governance |
| OCC copilot / agentic coordination | LLM over ops data plus tools | Vendor roadmaps only [S-O26][S-O27] | Unproven; advisory only |

**Where AI is not the answer:** INVOL reissue, MCT legality, regulatory eligibility, crew legality checks and notification deadlines are deterministic rules [03 §1][04 §1].

## 11. Technical Research and Potential Approaches

- **A candidate architecture** to evaluate, not a decision:
  - an event-driven operational data layer that normalises Type B, MVT, NM B2B, A-CDM and PSS events into one state;
  - a rules engine for legality and rights;
  - a propagation and impact service covering tails, crew and passenger journeys;
  - ML risk scores;
  - an optimisation-based recovery engine with explanations;
  - human acceptance in OCC/PCU tools;
  - a feedback loop from acceptances and outcomes [02 §7][03 §7][05 §8].
  `[AI-OPP]`
- **Research to follow:**
  - ML-accelerated recovery MIP (Hizir, Barnhart & Vaze 2026) [S-N33];
  - RL-guided neighbourhood search [S-N34];
  - integrated recovery models (Petersen et al. 2012; Bratu & Barnhart 2006) [S-N28][S-N29];
  - EUROCONTROL/MUAC take-off-time prediction, about 30% less error at EOBT-1h [S-P36];
  - network-state delay models [S-P40].
- **Metrics:** passenger-centric metrics (passenger delay minutes, misconnects, overnight strandings), plus OTP15, cost, compensation and fairness distribution KPIs [03 §1][04 §9].

## 12. Challenges, Risks and Limitations

- **Data integration and quality** dominate cost. Delay-cause labels are noisy and not harmonised (AHM 730/731 vs 732, BTS buckets, CODA coverage) [01 §1][02 §1].
- **Explainability and trust:** controllers accept only some suggestions (26% of changes at OPSD), and decision time is short [S-N31].
- **Legal:** GDPR special-category data, automated decisions (Art. 22) and discrimination ("unjust prejudice" in 14 CFR 250). Obligations also shift with EU261 reform in 2027 [04 §8].
- **Vendor lock-in and legacy messaging:** Type B carries no ordering guarantee and no security [S-O09].
- **Evidence quality:** most performance figures are self-reported by vendors or airlines; several sources were read only through search extracts. Industry cost-of-disruption estimates conflict (US$25–60bn a year, from 2007–2016 sources) [02 §8].
- **Business-model differences:** solutions do not transfer directly between LCC, hub and regional carriers [§2].

## 13. Unanswered Questions and Knowledge Gaps

Airline-specific questions to ask first. They are consolidated from the notes, where full lists are in each note's open-questions section.
1. **Systems:** which PSS, OCC, crew, M&E and flight-planning systems (vendor and version) are in use, and which real-time feeds exist (Type B, AIDX, NM B2B, A-CDM, SWIM, ACARS, OEM health)? Is a re-accommodation module licensed?
2. **Authority:** the decision rights and delegation matrix. Who approves swaps, cancellations, holds, interline protection and hotel spend, and what are the decision deadlines?
3. **Cost:** the cost model (delay cost per minute, compensation exposure per regime, care costs, crew overtime) and the false-alarm vs miss trade-off for predictions.
4. **Priority:** the internal rebooking priority order (not only denied boarding), use of FFP/CLV, corporate SLAs, alliance/JV agreements, and the fairness KPIs it will accept.
5. **Crew:** union contract rules on reassignment and reserves.
6. **Interline:** partners with bilateral IROPS inventory agreements, MCT exceptions and overrides at its hubs, and the status of the FIM.

Research gaps for the next pass:
- final OJ text of Reg. (EU) 2026/2202;
- CODA 2024 final and 2025 figures;
- the EASA ORO.OCP final text;
- current DGCA, ANAC, APPR and GCAA texts;
- AIRIMP primary text (PNR elements, SSR list);
- the DCS messages PNL/ADL/PTM/PSM;
- ATPCO categories for involuntary reissue;
- vendor solve times;
- full results of the RL and ML-MIP papers;
- whether the Delta, Google and United ConnectionSaver tools are still in use;
- revenue management's role in IROPS;
- coordination-call practice;
- segment-level (LCC, hub, regional) delay data.

## 14. References and Source Links

All 261 sources, with tier, publisher, date, URL and access date, are in `../../SOURCES.md`, grouped by note. Twenty sources are cited by more than one note; the registry lists them, and they are the cross-checked core (for example, the IATA Interline IROPS guidance, the DOT Southwest consent order, the INFORMS OPSD paper, the US refund rule, and the Amadeus Passenger Recovery material).

## 15. Airline-specific findings from the UC5 requirement (added 2026-11-20)

UC5 (input/requirements/Disruption_Management_UC5.docx, the briefing transcript and the product-owner Q&A of 2026-11-20) turned this topic into a product requirement for an Air Arabia–group network with its hub at Sharjah (SHJ). These facts are specific to that airline and close or narrow some of the §13 gaps. Aggregates only; the details are in `execution/QUESTIONS_UC5.md` and the git-ignored `input/data/disruption-uc5/synthetic/README.md`.

- **Seat capacity** comes from the inventory allocation, not the aircraft: **CURTAIL** lowers a flight's sellable limit (e.g. 170 → 160) and **OVERSELL** raises it. A recovery model must use the curtailed or oversold capacity. `[SPECIFIC]` (product owner)
- **Connection window at SHJ:** 15 min to 20 h. A published hub MCT table covers 39 routings through SHJ at 50–55 min, with a 1,200 min maximum. Compare the IATA MCT standards in [03 §1]. `[SPECIFIC]`
- **Recovery levers accepted:** aircraft swap, equipment change, delay and cancellation. Build two first: delay and same-type aircraft swap. `[SPECIFIC]` (product owner)
- **Bookings and inventory can disagree** at any moment, because sales run in parallel and booking extracts lag. The process must keep working when they don't match. This adds a data-latency constraint to [05 §1] (late or out-of-order data). `[SPECIFIC]`
- **The decision model is advisory.** The briefing describes OCC, crew control and the PCU working with different information, and asks for an agent that combines impact, evaluates options and explains its recommendation. This matches the human-in-the-loop pattern in §5 and [05 §8]. `[SPECIFIC]`
- **Delay-cause mix (Jan–Nov 2026 punctuality data, G9 only):** reactionary codes 91–96 make up about 76% of coded delay minutes, departure and arrival codes counted together. That is far above the 46% European average [S-N01]. Knock-on delay through aircraft rotation dominates at this LCC hub, which supports the propagation-first approach in §10. `[SPECIFIC]` `[VALIDATE]` (coding practice)
- **Data gaps confirmed at this airline:** no loyalty tier, no passenger identity beyond the name, no SSRs, no crew data, and no fare-family mapping in the supplied extracts. These are the §13 questions 1, 4 and 5 in practice. They are filled with labelled synthetic data for the prototype. `[VALIDATE]`

