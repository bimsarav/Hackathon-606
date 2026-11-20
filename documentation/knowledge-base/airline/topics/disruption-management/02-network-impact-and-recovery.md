# 02 – Network Impact Assessment & Recovery Strategy Optimization

> Scope: MASTER_PROMPT §15.7.2 (Network Impact Assessment) and §15.7.5 (Recovery Strategy Optimization).
> Guiding question: *How can AI help an airline predict, assess and minimise the impact of flight disruptions on its network and passengers?*
> Status: first research pass, 2026-11-20. Labels: `[STD]` standard/regulation · `[PRACTICE]` common practice · `[SPECIFIC]` one airline/vendor · `[ACADEMIC]` research · `[AI-OPP]` potential AI improvement · `[VALIDATE]` confirm with an airline.
> Related notes (same folder): [00-OVERVIEW](00-OVERVIEW.md) · [01 prediction](01-disruption-prediction.md) · [02 network impact & recovery](02-network-impact-and-recovery.md) · [03 passenger impact](03-passenger-impact.md) · [04 prioritisation & rights](04-passenger-prioritization-and-rights.md) · [05 OCC/PCU & systems](05-occ-pcu-workflows-and-systems.md). Sources: [`../../SOURCES.md`](../../SOURCES.md) (IDs are namespaced per note and final; no renumbering). Glossary: [`../../GLOSSARY.md`](../../GLOSSARY.md).

---

## 1. Key findings

- **[STD] Reactionary delay is the largest single delay cause in Europe.** In 2023, reactionary (knock-on) delay made up 46% of all delay minutes in the ECAC area, or 8.1 minutes per flight, the same share as in 2022 [S-N01]. Network propagation, not the original event, dominates delay. A 2024 figure of 46% / 8.0 min was seen only in a search summary of a draft digest, so treat it as [VALIDATE].
- **[STD] The IATA delay codes already encode the propagation mechanism.** Codes 91–96 (RL load connection, RT through check-in, RA aircraft rotation, RS cabin crew rotation, RC crew rotation, RO operations control re-routing/consolidation/aircraft change) separate reactionary causes by resource [S-N01][S-N53]. This is the label set any propagation model should learn from.
- **[SPECIFIC] The best-documented production system for integrated recovery is Lufthansa Group / Google "OPSD"** (INFORMS IJAA, Jan–Feb 2026, Edelman Award) [S-N31]. It jointly handles aircraft, passengers and crew using column generation, large neighbourhood search (LNS), MIP and a black-box crew-feasibility checker. It is in daily use at SWISS and being rolled out across LHG. Its controllers accepted 222,714 solver changes, 26% of all their changes since January 2022. It claims EUR 12 M and 14 kt CO2 saved so far, with EUR 30 M a year targeted. About 20 developers spent four years on **data preparation**, against five on the solvers. Data integration, not algorithms, is the dominant cost.
- **[PRACTICE][ACADEMIC] Two time scales.** Recovery happens in minutes ("we cannot rebook passengers on a flight departing in 30 minutes if making that decision requires 45 minutes") [S-N31]. Re-optimisation of tomorrow's plan can run overnight. Most of OPSD's monetary savings came from the simpler overnight **Schedule Optimizer**, not the real-time IrrOptimizer [S-N31].
- **[PRACTICE] Crew is usually the binding constraint and the usual point of failure.** Southwest Dec 2022 (≈16,700–16,900 cancellations, >2 M passengers stranded, record US$140 M DOT penalty) and Delta Jul 2024 (>7,000 cancellations, ≈1.3 M customers, ≈US$550 M cost) both turned into multi-day meltdowns when crew-tracking and reassignment processes or tools could not absorb the volume of changes [S-N02][S-N03][S-N04][S-N08][S-N09][S-N11]. In both cases aircraft were mostly available.
- **[STD] Crew legality rules are hard constraints with exact numbers.** In the US (14 CFR Part 117), the maximum unaugmented FDP is 9–14 h by start time and segment count. The minimum rest is 10 h including an 8 h sleep opportunity, plus 30 consecutive hours free in any 168 h. A pre-takeoff extension of up to 2 h is allowed, and only once may it exceed 30 min before qualifying rest [S-N12–S-N15]. Under EASA (ORO.FTL), the basic maximum FDP is 13:00 for 1–2 sectors, reduced 30 min per extra sector. Commander's discretion allows up to +2 h (+3 h augmented), and minimum rest is the longer of the preceding duty or 12 h at home base / 10 h away [S-N17][S-N18].
- **[STD] Passenger-rights rules shape which recovery actions are cheap.** EU261 Art. 8 requires re-routing "at the earliest opportunity"; Art. 5/7 tie compensation to notice time and re-routing timings [S-N49]. The US DOT 2024 refund rule defines a "significant change" as >3 h domestic or >6 h international [S-N50]. These thresholds create sharp cost jumps that a recovery optimiser must model.
- **[ACADEMIC] Integrated recovery outperforms sequential (aircraft → crew → passengers) recovery** in the literature (Petersen et al. 2012; Bratu & Barnhart 2006). Adoption in OCCs is still limited by data integration, scalability, explainability and adaptability [S-N28][S-N29][S-N32][S-N26].
- **[ACADEMIC] ML and RL play a supporting role, not the main one.** The strongest recent results are **hybrids**: supervised ML that predicts which recovery decisions are likely, used to shrink a MIP (Hizir, Barnhart & Vaze 2026, at a major US airline with >2,800 daily flights) [S-N33], or RL guiding a neighbourhood search [S-N34]. Pure-RL recovery results are research-only and, in some studies, "far from optimal" [S-N35].
- **[PRACTICE] The industry cost of disruption is large, but the figures conflict.** Estimates range from US$25 bn a year (GE, uncited) to 5% of revenue ≈ US$35 bn (T2RL 2016) to 8% ≈ US$60 bn including passenger costs (T2RL/Amadeus 2016). The US-only 2007 figure was US$32.9 bn total, of which US$8.3 bn fell on airlines (NEXTOR 2010) [S-N44][S-N45][S-N46][S-N48]. See section 8.

---

## 2. Domain fundamentals & terminology

| Term | Meaning | Source |
|---|---|---|
| IROPS | Irregular operations: deviations from the planned schedule (weather, ATC, technical, crew, IT). | [S-N45][S-N31] |
| Primary vs reactionary delay | Primary delay originates at the flight itself. Reactionary (knock-on) delay is inherited from an earlier flight through aircraft, crew, passengers or load. | [S-N01] |
| Reactionary delay codes 91–96 | RL load connection, RT through check-in error, RA aircraft rotation, RS cabin crew rotation, RC (cockpit/entire) crew rotation, RO operations control (re-routing, diversion, consolidation, aircraft change for non-technical reasons). | [S-N01][S-N53] |
| Rotation / tail assignment / line of flying | The ordered sequence of legs flown by one registration (tail). Tail assignment maps legs to specific aircraft subject to turn times and maintenance. | [S-N31][S-N36] |
| Minimum turnaround time (MTT) | The shortest feasible ground time between consecutive legs of one aircraft. It is a hard constraint in tail assignment. | [S-N31] |
| Crew pairing / trip | A sequence of FDPs that starts and ends at the crew's home base. Crew connections need not follow the aircraft. | [S-N31][S-N45] |
| FDP | Flight duty period: from report time to the end of the last flight's block-on, limited by regulation. | [S-N12][S-N17] |
| Deadheading | Crew travelling as passengers to reposition. It consumes seats that passenger recovery needs. | [S-N31][S-N04] |
| Reserve / standby crew | Crew held available to cover open trips. A primary crew-recovery lever. | [S-N31][PRACTICE] |
| AOG | Aircraft on ground: the aircraft is unserviceable and cannot be dispatched. Triggers swap, delay or cancellation. | [S-N36][PRACTICE] |
| MEL | Minimum Equipment List: allows dispatch with specified inoperative items under conditions (14 CFR 121.628). Decides whether a defect becomes an AOG. | [S-N55] |
| Hub bank / wave | A timed cluster of arrivals followed by departures at a hub, built for connections. A delay to the bank spreads to many onward flights. | [S-N30][PRACTICE] |
| Point-to-point / "nodal" network | Aircraft and crew route through many stations rather than a few hubs. It has fewer connections but long multi-station aircraft and crew lines. | [S-N30][S-N05] |
| ATFM slot / CTOT | Calculated take-off time issued by the EUROCONTROL Network Manager. Tolerance −5/+10 min. | [S-N20][S-N21] |
| GDP / EDCT / Slot Credit Substitution | US Ground Delay Program issues EDCTs. Under CDM, airlines can swap or substitute their slots (e.g. cancel f1 to move f2 up). | [S-N22] |
| Airport slot (coordinated, Level 3) | Permission to use the airport's infrastructure on a given date and time. Historic precedence needs ≥80% use of a slot series ("80/20" rule) under the IATA WASG. | [S-N19] |
| Curfew / night ban | Legal limit on night movements (e.g. Sydney 23:00–06:00 under the Sydney Airport Curfew Act 1995; Frankfurt 23:00–05:00). | [S-N23][S-N24] |
| A-CDM / TOBT / TSAT | Airport Collaborative Decision Making: milestone approach; target off-block time (from airline or handler) and target start-up approval time. DPI messages to the Network Manager. | [S-N54] |
| ASM / SSM | IATA SSIM ad-hoc schedule message (Chapter 5) and standard schedule message (Chapter 4), used to publish schedule changes. | [S-N52] |
| MVT | IATA AHM 780 movement message (departure/arrival/delay with delay codes). | [S-N53] |
| Involuntary reroute / Res. 735d | IATA resolution governing involuntary change of carrier, routing, class or fare. Binds IATA members and MITA participants. | [S-N51] |
| FIM | Flight Interruption Manifest: interline document for moving disrupted passengers. IATA guidance treats it as a last resort. | [S-N51] |
| Disruption recovery vs re-optimisation | The real-time repair problem (minutes) versus improving the next days' plan once stable (hours, overnight). | [S-N31] |

---

## 3. Processes, decisions & timing

### 3.1 Network impact assessment: how disruption propagates
1. **Aircraft rotation.** A late inbound aircraft delays its next leg unless slack (scheduled ground time beyond MTT) absorbs it. AhmadBeygi et al. showed that schedules optimised for utilisation leave little slack, so delays propagate down the rotation. They compared a hub carrier with a point-to-point LCC [S-N30]. **[ACADEMIC]** CODA notes that schedulers deliberately add block-time "padding", and that airlines take one or two IATA seasons to adapt schedules after delay patterns change [S-N01]. **[STD/PRACTICE]**
2. **Crew connections.** Crew often change aircraft. A delayed inbound can strand a crew needed elsewhere, or push them past their FDP limit, and "a longer-than-expected flight might trigger a compulsory break for the crew, rendering that crew unavailable" [S-N31]. Keeping crews together through an FDP limits that spread [S-N31]. **[PRACTICE]**
3. **Passenger and load connections.** At hubs, missed connections create rebooking demand on later flights, and holding a departure for connecting passengers delays its own downstream rotation (code 91 RL) [S-N01]. **[STD]**
4. **Airport and airspace constraints.** ATFM regulations (CTOT), GDPs (EDCT), curfews and slot rules cap how much retiming is possible. A curfew turns a late flight into a cancellation or diversion [S-N20][S-N22][S-N23]. **[STD]**
5. **Aircraft availability.** AOG events, MEL items and maintenance due windows (aircraft must reach planned checks at a maintenance station) remove aircraft or fix where they must be [S-N36][S-N31][S-N55]. **[PRACTICE]**
6. **Network-wide cascade.** When crew and aircraft fall out of position faster than they can be reassigned, the airline loses track of resources and is forced into mass cancellation and a reset (Southwest 2022, Delta 2024) [S-N04][S-N05][S-N11]. **[PRACTICE]**

### 3.2 Recovery levers (roughly in order of escalating impact) **[PRACTICE]**
| Lever | Typical use | Key constraints / side-effects | Source |
|---|---|---|---|
| Retime / delay | Absorb short delays, wait for connecting pax or crew | Crew FDP, curfews, CTOT/EDCT, downstream misconnects | [S-N31][S-N36] |
| Aircraft swap (same type) | Move a ready tail onto a delayed rotation | Maintenance routing, crew type qualification unaffected | [S-N31][S-N36] |
| Equipment / sub-fleet change (up/down-gauge) | Capacity for rebooked pax, or replace an AOG | Different crew qualifications/complement, so crew changes nearly always needed | [S-N31] |
| Rotation change / re-routing | Rebuild tail lines across stations | Maintenance station visits, MTT | [S-N36] |
| Consolidation | Combine low-load frequencies | Passenger rights for the cancelled flight; code 96 RO | [S-N01] |
| Cancellation (often round-trip pairs) | Restore aircraft/crew balance quickly | EU261/DOT obligations; slot usage (80/20) | [S-N49][S-N50][S-N19][VALIDATE: round-trip pairing practice] |
| Ferry / repositioning flight | Move aircraft (or crew) without revenue | Cost, crew time; Southwest ran >500 empty repositioning flights per SWAPA | [S-N36][S-N04] |
| Wet lease / ACMI | Cover longer capacity gaps (AOG, fleet groundings) | Lead time hours to days; regulatory approval of lessor | [VALIDATE] (no Tier 1–2 source gathered in this pass) |
| Crew reserves / standby | Cover sick or illegal crew | Reserve availability rules, call-out lead time | [S-N31][PRACTICE] |
| Crew deadheading | Reposition crew | Uses seats; counts toward duty (Part 117 deadhead rules) | [S-N31][S-N15] |
| Crew swap / trip repair | Re-pair crews across flights | Legality, qualifications, contractual reassignment limits | [S-N31][S-N45] |
| Passenger reroute / rebook (own, alliance, interline) | Protect itineraries | Seat inventory, Res. 735d, MCT, groups | [S-N31][S-N42][S-N51] |
| Ground expedite (e.g. LHG ramp direct service vehicles) | Save tight hub connections | Limited fleet of vehicles | [S-N31] |

### 3.3 Decision timing **[PRACTICE]/[SPECIFIC]**
- **Minutes.** Day-of-operations repairs must be feasible before the affected departures. OPSD's priority is "quickly find an acceptable decision, which is preferable to an optimal one that requires hours" [S-N31]. Its passenger solver runs a greedy heuristic first, then a parallel portfolio (multicommodity flow, column generation) under a time limit [S-N31].
- **Tens of minutes.** Research prototypes target about 10 min end to end, e.g. Rodrigues et al. ≈552–568 s per full run [S-N32]. Vendor material cites solutions "within 70 minutes" for all passengers in one Amadeus scenario. That is marketing, not a benchmark [S-N46].
- **Hours or overnight.** Re-optimisation of the next one to three days. At SWISS a full controller shift was previously spent preparing the next day's tail assignment. Manual work changed at most about 20 rotations, while OPSD regularly changes >100 rotations over three days [S-N31].
- **Pre-emptive.** Cancelling early before forecast events is a known practice. One industry executive argued that cancelling 200–300 legs pre-storm "beats canceling 600–800 during the recovery" [S-N05]. That is opinion (Tier 4), consistent with HEAT's use only "when there is high confidence in the forecast" [S-N47].

### 3.4 Manual vs tool in practice
- **[SPECIFIC]** At SWISS, before OPSD, recovery was "largely manual", with teams of controllers per department (aircraft, passengers, crew) and decoupled systems that needed manual cross-checking [S-N31]. Even with OPSD, 74% of changes are still made manually. Users edit proposed scenarios "because of factors that are as yet unknown to the system" [S-N31].
- **[PRACTICE]** Airlines prefer *interactive* decision support that extends the controllers' manual process over fully automatic "all-or-nothing" solutions, because controllers must understand and trust the result [S-N45]. Lufthansa Systems' aiOCC states that "the decision itself always remains with the operations controller" [S-N37].
- **[SPECIFIC]** American's HEAT is run by a coordinator team in the Integrated Operations Center. It checks crew rest and availability first, then passenger connections, then re-times arrivals and departures at the hub [S-N47].

---

## 4. Data requirements

| Data | Origin system (typical) | Update frequency | Standard / format | Notes / source |
|---|---|---|---|---|
| Published schedule & changes | Scheduling system, OCC | Seasonal (SSM); intra-day (ASM) | IATA SSIM Ch. 4 SSM, Ch. 5 ASM | [S-N52] |
| Actual movements (OUT/OFF/ON/IN, ETD/ETA) and delay codes | DCS/handling, ACARS, OCC | Event-driven (seconds to minutes) | IATA AHM 780 MVT; delay codes AHM 730 (newer AHM 732) | Some airlines add non-standard sub-codes [S-N53] |
| Tail assignment / rotations | OCC system (e.g. NetLine/Ops++, CAE Movement Manager, IBS iFlight Ops) | Continuous | Vendor-specific | [S-N36][S-N38][S-N41] |
| Maintenance plan, due checks, MEL/deferred items, AOG status | M&E system (MIS) | Event-driven + daily | Vendor-specific; MEL per 14 CFR 121.628 | Separate database from crew and pax at LHG [S-N31][S-N55] |
| Crew rosters, qualifications, duty/rest accumulators, location | Crew management/tracking system | Continuous; failures here caused Delta 2024 | Vendor-specific; rules coded per FAA/EASA plus CBA | [S-N31][S-N11] |
| Crew rules (legality + union contract) | Crew system rule engine | On regulation or contract change | Rule language; OPSD uses a black-box checker that users program | [S-N31] |
| Passenger bookings (PNRs, itineraries, groups, SSRs, FFP tier) | PSS (reservations, inventory) & DCS | Continuous | PNR/EDIFACT (PADIS), NDC/ONE Order (see passenger note) | [S-N31][S-N42] |
| Seat inventory / availability (own + partners) | Inventory / RM system; partner availability | Real-time | AVS/AVA messages, interline agreements [VALIDATE] | [S-N42] |
| Connection times (MCT) & per-passenger connection speed | MCT database; airport process data | Seasonal + event | IATA MCT [see passenger note] | LHG models Schengen/immigration and priority lanes [S-N31] |
| ATFM regulations & slots (CTOT), GDP/EDCT | EUROCONTROL NM (B2B); FAA TFMS/FSM | Minutes | NM B2B; FAA CDM messages | [S-N20][S-N22] |
| Airport constraints (curfews, slot holdings, capacity reductions) | Airport authority, coordinator, NOTAM | Static + event | WASG; national law; NOTAM | [S-N19][S-N23] |
| A-CDM milestones (TOBT, TSAT) | Airport CDM platform | Minutes | EUROCONTROL A-CDM; DPI messages | [S-N54] |
| Weather (current/forecast) | Met providers | 15 min – hourly | METAR/TAF, etc. | Input to HEAT [S-N47] |
| Cost parameters (delay cost, pax compensation, hotel, crew overtime, ferry, fuel) | Finance/RM; contracts | Periodic | Internal | OPSD "well calibrated" cost tool; NetLine MoneyMachine [S-N31][S-N36] |

**[PRACTICE] Data integration is the hard part.** OPSD built a standardised "base data layer" with airline-specific adapters, because crew, maintenance and bookings live in separate databases that also differ between LHG airlines. Inconsistencies (e.g. a flight departing mid-maintenance) must be auto-resolved because solves run many times a day [S-N31].

---

## 5. Business rules & constraints

| Rule | Type | Hard / soft | Detail | Source |
|---|---|---|---|---|
| US flightcrew FDP (unaugmented) | Regulatory | Hard | Table B: 9 h (0000–0359 start) to 14 h (0700–1159, 1–2 segments), decreasing with segments | [S-N12] |
| US FDP extension | Regulatory | Hard (bounded) | Up to 2 h pre-takeoff (PIC + certificate holder). An extension >30 min only once before 117.25(b) rest. Report to FAA within 10 days if >30 min; corrective action within 30 days if controllable | [S-N13] |
| US cumulative limits | Regulatory | Hard | Flight time ≤100 h/672 h, ≤1,000 h/365 days; FDP ≤60 h/168 h, ≤190 h/672 h | [S-N14] |
| US rest | Regulatory | Hard | 10 h rest incl. 8 h uninterrupted sleep opportunity; 30 consecutive h free in any 168 h; 56 h after >168 h trips crossing >60° longitude | [S-N15] |
| US flight attendants | Regulatory | Hard | 14 CFR 121.467: duty normally ≤14 h; 10 h minimum rest for duty ≤14 h (FAA Reauthorization Act 2018 §335, final rule 87 FR 61452, Oct 2022) | [S-N16] |
| Part 121 subparts Q/R/S | Regulatory | Hard | Older flight-time rules that remain relevant mainly to all-cargo ops not opting into Part 117 | [VALIDATE]: not verified in this pass |
| EASA basic FDP | Regulatory | Hard | Acclimatised, 0600–1329 start: 13:00 for 1–2 sectors, −30 min per extra sector, floor 9:00. Planned extension +1 h max twice per 7 days | [S-N17] |
| EASA commander's discretion | Regulatory | Hard (bounded) | Up to +2 h (+3 h augmented). Rest may be reduced but not below 10 h. Report to operator; to the authority if >1 h, within 28 days. Non-punitive process required | [S-N17] |
| EASA rest | Regulatory | Hard | Home base: max(preceding duty, 12 h); away: max(preceding duty, 10 h) incl. 8 h sleep opportunity; 36 h incl. 2 local nights recurrent within 168 h | [S-N18] |
| EASA duty | Regulatory | Hard | 60 duty hours in any 7 consecutive days (other ORO.FTL.210 limits not verified here) | search summary of ORO.FTL.210 [VALIDATE] |
| Union contract terms (reassignment limits, pay protection, hotel, days off) | Contractual | Hard to the company (grievance risk); soft in cost | Vary by airline and craft. Examples seen only on forums (e.g. 50% add-pay for reassignment into a day off) | [VALIDATE]: obtain the airline's CBA |
| MEL dispatch conditions | Regulatory | Hard | Inoperative items allowed only per an approved MEL and ops specs | [S-N55] |
| Maintenance due windows | Regulatory/OEM-driven | Hard (by deadline) | Recovery must route aircraft to checks in time | [S-N36][S-N31] |
| ATFM slot (CTOT) | Regulatory | Hard | −5/+10 min tolerance. Swaps only between flights under the same measure, max 3 per flight (per EUROCONTROL networker guide) | [S-N20][S-N21] |
| US GDP / EDCT | Regulatory/ATC | Hard | Airlines may substitute slots within their allocation under CDM; ATCSCC may deny | [S-N22] |
| Curfews | Regulatory (national law) | Hard | e.g. Sydney 23:00–06:00, fines >AUD 1.1 M, dispensations only in exceptional cases | [S-N23] |
| Slot retention (80/20) | Industry standard / EU law | Soft (season-level) | Cancellations count against usage. Waivers have applied (COVID, local alleviation) | [S-N19] |
| EU261 re-routing & compensation | Regulatory | Hard (care/rerouting); compensation waived only for extraordinary circumstances | Art. 8 re-route at earliest opportunity; Art. 5 notice thresholds (≥14 days, 7–14 days, <7 days with re-routing windows); Art. 7 fixed compensation | [S-N49] |
| US refunds | Regulatory | Hard | Automatic refund on cancellation or significant change (>3 h domestic, >6 h international) if the passenger declines alternatives; effective 25 Jun 2024 | [S-N50] |
| Interline involuntary reroute | Industry standard | Hard among IATA/MITA parties | Res. 735d; LCCs that are not IATA/MITA members fall outside it | [S-N51] |
| Commercial priorities (high-value pax, groups together) | Commercial | Soft | Allowed only within the legal protections above | [S-N42][S-N31] |
| Crew stay-together, minimise crew changes | Operational policy | Soft | Lower weight in OPSD than aircraft/pax costs | [S-N31] |

**[PRACTICE] Rule of precedence:** safety and regulatory constraints → legal passenger rights → contractual (CBA) → operational policy → commercial preference. Commercial value must never override the first three (MASTER_PROMPT §15.7.4).

---

## 6. Industry practice & real-world cases

### 6.1 Southwest Airlines, 21–31 Dec 2022 (winter storm Elliott → crew-network collapse)
- **Scale:** about 16,700 cancellations per AP/KSL [S-N04], or 16,900 per DOT [S-N02][S-N03]. More than 2 million passengers stranded. Flag: the counts differ slightly by source and window.
- **Cause (airline's account):** COO Andrew Watterson's written Senate testimony (9 Feb 2023) said storm recovery "created an unprecedented amount and frequency of required changes to Crew schedules that overwhelmed our Crew Scheduling processes and technology" [S-N04]. Press reports said he described winter-operations failures (notably Denver and Chicago Midway) as the start and crew scheduling as the last domino. Those statements were seen only in search summaries, so treat them as [VALIDATE].
- **Union account:** SWAPA said Southwest "averaged one major operational failure every 18 months" since 2011. It reported >500 empty repositioning flights and >10,000 pilots deadheading [S-N04]. Dispatcher messages show schedulers could not confirm who was operating flights [S-N04].
- **Tooling (conflicting sources):** Wikipedia describes SkySolver and Crew Web Access as proprietary, internally maintained programs [S-N07]. Press summaries of the testimony say Southwest was testing an upgrade to crew-scheduling software from GE Digital (search summary only). Flag: the ownership and vendor of SkySolver are unresolved [VALIDATE].
- **Regulatory outcome [STD]:** On 18 Dec 2023, DOT imposed a US$140 M civil penalty, 30 times larger than any previous DOT consumer-protection penalty. US$35 M is paid in cash. A US$90 M compensation system covers future controllable cancellations and significant delays, with a US$72 M offset credited against the penalty. Combined with more than US$600 M in refunds and reimbursements, the total exceeds US$750 M. The findings covered refunds, timely flight-status notifications and customer service; DOT did not penalise the operational failure as such [S-N02][S-N03].
- **Lessons [PRACTICE]:** (1) Crew-location visibility is a single point of failure. (2) A point-to-point network with many crew bases makes crew re-pairing combinatorially harder [S-N05]. (3) Cancel early and deliberately rather than late and chaotically [S-N05]. (4) Passenger-communication failures carry their own regulatory liability.

### 6.2 Delta Air Lines, 19–25 Jul 2024 (CrowdStrike/Windows outage)
- **Scale:** >7,000 cancellations, about 1.3–1.4 M customers affected; normal operations by about 25 Jul [S-N08].
- **Cause:** CEO Ed Bastian said "one of our crew tracking-related tools was affected and unable to effectively process the unprecedented number of changes triggered by the system shutdown" [S-N11]. Other US carriers recovered within about a day, which DOT cited as "a very different pattern from Delta" [S-N11].
- **Cost:** about US$380 M revenue impact (refunds, cash and SkyMiles compensation) plus about US$170 M non-fuel expense, partly offset by about US$50 M fuel saving. Bastian had first estimated US$500 M [S-N09].
- **Regulatory outcome:** DOT opened an investigation on 23 Jul 2024 [S-N11]. It was closed with no penalty; Reuters reported this on 15 Jun 2026, with some reports saying it was closed in Nov 2025. DOT found refunds, baggage handling and disability assistance adequate [S-N10]. DOT classified the event as controllable [S-N08]. Flag: the closing date is inconsistent across reports.
- **Lessons [PRACTICE]:** an IT outage becomes a *crew-recovery* crisis. Recovery tools need to be resilient (failover, degraded modes) and to scale to orders of magnitude more change events than normal.

### 6.3 Lufthansa Group / SWISS + Google, OPSD (2019–2026) [SPECIFIC]
- Integrated aircraft + passenger + crew recovery (IrrOptimizer) and next-days re-optimisation (Schedule Optimizer) [S-N31].
- Schedule Optimizer used on 1,038 days (Jan 2022–Jan 2025) and published as the plan of record 6,797 times. 222,714 solver changes accepted, 26% of all changes, touching 24.7% of SWISS flights. CHF 8.5 M operating cost and 14.7 kt CO2 directly attributed to it by Jan 2025 [S-N31]. Flag: the abstract cites "EUR 12 million"; the body cites CHF 8.5 M for the Schedule Optimizer only. The basis of the two figures differs.
- Passenger subsolver live since Feb 2025. Passengers are now rerouted **as soon as disruption becomes apparent**, not after reaching the hub. In one anecdote the solver's plan for a long-haul AOG was >US$200k cheaper than a 10-year controller's plan [S-N31].

### 6.4 American Airlines HEAT (2022–) [SPECIFIC]
- An in-house Hub Efficiency Analytics Tool that re-times arrivals and departures at hubs ahead of severe weather. Inputs are weather, loads, connections, gates, ATC and crew constraints. The airline claims it prevented "nearly 1,000" cancellations in its first year and ">1,000" by 2024 (company claims, unverified) [S-N47].

### 6.5 Air Canada + Amadeus Passenger Recovery [SPECIFIC, vendor-reported]
- About 90% of cancellation handling automated; rebooking about 10 min versus about 12 h previously (Amadeus-published) [S-N43]. The product rebooks onto other carriers and lets airlines prioritise high-value passengers [S-N42].

### 6.6 Commercial tools: verified names and claims **[SPECIFIC]**
| Vendor | Product(s) verified | What they claim (vendor material) | Source |
|---|---|---|---|
| Lufthansa Systems | NetLine/Ops ++ (OCC); NetLine/Ops ++ Solver xOPT & Tail xOPT; NetLine/Crew; NetLine/Hub; aiOCC assistant | Rotation recovery respecting maintenance and airport opening hours; delay/ferry/cancel trade-off via tunable costs; propagates delays along crew connections; scenario pre-planning (e.g. strike closure); MoneyMachine costing; aiOCC is recommendation-only | [S-N36][S-N37] |
| CAE (ex-Sabre AirCentre, acquired 28 Feb 2022; now branded Flightscape) | Movement Manager, Recovery Manager Ops, Crew Management, Unified Task Board (2024) | Recovery considering fuel, pax and crew costs, audit trail; acknowledges aircraft swaps fail without crew feasibility | [S-N38][S-N39] |
| Jeppesen ForeFlight (sold by Boeing to Thoma Bravo, 2025, ~US$10.55 bn) | Crew tracking, flight planning, dispatch | Continues crew-tracking tools; AI "to the OCC" stated in general terms only. Product-level recovery claims not verified | [S-N40] |
| IBS Software | iFlight Ops / iFlight NEO (BA 2018; Air France-KLM >500 aircraft) | Real-time OCC situational awareness, disruption management, tail-assignment decision support | [S-N41] |
| Amadeus | Passenger Recovery, Schedule Recovery (named in infographic), Self Re-accommodation | Automated rebooking incl. other carriers; prioritisation; Air Canada results | [S-N42][S-N43][S-N46] |
| GE Aerospace | Network Operations Optimization (SaaS) | Detects disruption impact up to 72+ h, compares multiple solver solutions | [S-N44] |
| Google | OPSD for LHG (built on Google's internal "Universal Optimization Solver Service") | See 6.3. **Not verified** that OR-Tools/CP-SAT is the engine: CP-SAT appears only in an author biography | [S-N31] |

---

## 7. AI / optimisation approaches

| Approach | Problem | Data needed | Solve time (reported) | Results reported | Maturity | Limitations | Source |
|---|---|---|---|---|---|---|---|
| Time-space network / multicommodity flow MIP | Aircraft recovery, passenger reroute | Rotations, MTT, maintenance, pax itineraries | Seconds to minutes at small/medium scale; scalability limits for large exact models | Standard formulation; basis of OPSD pax portfolio | Proven (production at LHG; vendor solvers) | Size explodes with time discretisation | [S-N25][S-N31][S-N32] |
| Set partitioning / covering with column generation | Crew recovery, integrated recovery | Crew trips, legality rules, costs | Minutes with heuristics/LNS | OPSD core; literature since 1990s | Proven | Needs good pricing and initial columns; rule engines complex | [S-N31][S-N32] |
| Large neighbourhood search embedded in CG; sequential heuristics | Integrated (aircraft-pax-crew) | All above | Within operational time limits (exact limits not published) | OPSD production | Proven (one airline group) | Near-optimal only; tuning effort | [S-N31] |
| Logic-based Benders with black-box crew checker | Tail assignment with crew feasibility | Crew rules as executable checker | Overnight re-optimisation | CHF 8.5 M saved (SWISS) | Proven | Crew approximations restrict the solution space | [S-N31] |
| Integrated recovery MIP (Petersen et al.) | Schedule + aircraft + crew + pax | Full network data | "Acceptable time" on test instances | Better than sequential approach | Research | Real-time at full scale unproven | [S-N28] |
| Passenger-centric models (Bratu & Barnhart) | Aircraft recovery with passenger delay costs | Pax itineraries, costs | Research-scale | Explicit operating-vs-passenger cost trade-off | Research | Cost calibration | [S-N29] |
| Constraint programming | Crew recovery feasibility | Legality rules | Not reported | Literature (Zhu et al. 2014, per review) | Research / niche | Optimisation quality | [S-N32] |
| Metaheuristics (GRASP, NSGA-II, ACO, simulated annealing) | Aircraft / integrated | As above | Fast | Mixed; many on synthetic data | Research | No optimality bound | [S-N32] |
| Supervised ML + MIP (decision prediction to prune the model) | Large-scale crew recovery | Historical recovery decisions, delay predictions | Faster than direct MIP (details not retrieved) | "tens of millions of dollars" estimated savings; more robust under uncertain delay predictions; major US airline >2,800 daily flights | Research with real data | Depends on historical decisions; distribution shift in rare events | [S-N33] |
| Deep RL + variable neighbourhood search (PPO) | Aircraft/integrated recovery | Simulated disruptions | Motivated by MINLP intractability; numbers not retrieved | Not retrieved | Research | Training cost, action-space limits | [S-N34] |
| Pure RL (aircraft swapping) | Aircraft recovery | Simulator | — | "far from being optimal", better than doing nothing | Research | Feasibility guarantees, explainability | [S-N35] |
| Analytics-driven hub re-timing (HEAT) | Pre-emptive hub schedule smoothing | Weather, loads, connections, gates, ATC, crew | Run before the event | ~1,000 cancellations avoided (claimed) | Production (one airline) | Needs confident forecast windows | [S-N47] |
| Predictive delay propagation (supervised ML) | Network impact estimation | Movement history, delay codes, rotations, crew links | Real-time inference | Literature (e.g. Lee & Jacquillat 2020 cited in [S-N32]) | Research → emerging production | Propagation depends on future decisions (counterfactual) | [S-N32][AI-OPP] |

**When OR beats ML [ACADEMIC/PRACTICE].** Recovery is a constrained combinatorial decision with hard legal rules (FDP, rest, curfews, MEL, passenger rights). Exact or heuristic optimisation gives feasibility guarantees, cost transparency and what-if scenarios. Every production system verified here (OPSD, NetLine xOPT, CAE Movement Manager) is optimisation-based [S-N31][S-N36][S-N38].

**Where ML fits [AI-OPP].** (a) Prediction feeding the optimiser: delay and propagation forecasts, likely AOG duration, crew sickness, passenger no-show/connection-make probabilities, passenger claim propensity. (b) Learning to optimise: predicting likely decisions to prune MIPs (as in [S-N33]), warm-starting, and choosing neighbourhoods (as in [S-N34]). (c) Calibrating cost functions such as passenger-inconvenience cost and goodwill.

**Where GenAI/LLMs fit [AI-OPP, unproven].** Explaining a proposed recovery plan to controllers and passengers, drafting crew and passenger notifications, and parsing free-text inputs (NOTAMs, MEL remarks). They are not a decision engine. No production evidence was found in this pass.

**Hybrid pattern (recommended for further study) [AI-OPP].** First, ML predicts impact. Next, optimisation generates several feasible scenarios with costs. Then a human selects and edits. Finally, accepted and edited decisions are logged as training data. This matches OPSD's human-in-the-loop acceptance data and the T2RL finding that controllers prefer interactive tools [S-N31][S-N45].

---

## 8. Risks, limitations, airline-model differences

- **[PRACTICE] Data integration and quality dominate.** About 20 developers over four years went on data versus five on solvers at LHG [S-N31]. Real-time inconsistencies between the maintenance, crew and movement systems must be resolved automatically.
- **[PRACTICE] Scale resilience.** Both Southwest and Delta failed when change volume spiked. Tools need load testing at orders of magnitude above normal, plus degraded modes [S-N04][S-N11]. OPSD uses per-solve process isolation and load shedding that prioritises solves a human is waiting on [S-N31].
- **[PRACTICE] Trust and explainability.** Controllers accept only part of the solver output (26% of changes at SWISS) [S-N31]. Black-box "all-or-nothing" solutions are rejected [S-N45].
- **[ACADEMIC] Counterfactual evaluation is hard.** Benefits such as robustness are "not quantitatively measured" even at LHG [S-N31]. Passenger-compensation savings take years to observe, because EU claims have a multi-year window [S-N31].
- **[STD] Cost-figure conflict.** GE says US$25 bn a year and US$281 per disrupted passenger (no source cited, undated) [S-N44]. T2RL (Sept 2016) puts airline cost at about 5% of revenue (≈US$35 bn), with ≈US$60 bn including lost productivity [S-N45]. The companion T2RL/Amadeus paper calls US$60 bn "8% of airline revenue" [S-N46], which is inconsistent with its sister paper. NEXTOR puts the 2007 US total at US$32.9 bn (US$8.3 bn airlines, US$16.7 bn passengers) [S-N48]; a later NEXTOR deck cites US$31.2 bn for the same year. All of these are **outdated (2007–2016)**. Use them only for orders of magnitude [VALIDATE].
- **Hub carriers vs LCC point-to-point [ACADEMIC/PRACTICE].**
  - *Hub carriers:* disruption propagates through **passenger connections and banks**. They have many reroute options at the hub and can cancel spoke round-trips to protect banks. Passenger recovery and interline/alliance options matter most [S-N30][S-N31].
  - *Point-to-point / LCC:* fewer connecting passengers, but **long multi-station aircraft and crew lines**. Southwest had about 4,000 daily departures and many crew bases, by a Tier 4 estimate [S-N05]. Crew re-pairing is harder and cancelling to the hub is not available. Many LCCs are not IATA/MITA interline parties, so Res. 735d reroutes are unavailable [S-N51].
  - *Regional / capacity-purchase:* the crew and aircraft are owned by a different operator from the marketing carrier, so recovery decisions span two companies [VALIDATE].
- **[STD] Regulatory regime differences.** FAA Part 117 and EASA ORO.FTL differ in structure: FAA uses tables by start time and segments with a 10 h rest; EASA uses a 13 h basic FDP, 12 h home-base rest and commander's discretion. Multi-AOC groups (LHG) need per-airline rule sets [S-N12][S-N17][S-N31].
- **[PRACTICE] Over-optimisation risk.** Squeezing slack raises propagation [S-N30]. OPSD deliberately penalises very short turns and rewards some long gaps for robustness [S-N31].

---

## 9. Open questions / knowledge gaps / items to validate with an airline

1. **[VALIDATE]** Which OCC, crew, M&E and PSS products the target airline uses, and their APIs or event feeds (MVT, ASM, crew events). This determines integration cost (see §4).
2. **[VALIDATE]** The airline's union contracts (CBAs): reassignment limits, pay protection, reserve call-out rules, hotel and deadhead terms. No authoritative CBA text was obtained.
3. **[VALIDATE]** Its cost model: delay cost per minute by fleet, passenger compensation exposure (EU261/UK261/DOT/other regimes), hotel/meal costs, crew overtime, ferry and wet-lease rates. No current Tier 1 figures were gathered for wet-lease lead times or costs.
4. **[VALIDATE]** Its decision rights: who can cancel or swap without approval, and the escalation thresholds (OCC duty manager, network control, crew control).
5. **[VALIDATE]** The full ORO.FTL.210 cumulative limits and the current consolidated EASA text. This pass used the UK CAA regulatory library copy of Reg. 965/2012, which may diverge post-Brexit. Part 121 subparts Q/R/S applicability was not verified.
6. **[VALIDATE]** The Southwest SkySolver provenance (in-house versus GE) and the Oliver Wyman findings. Southwest's July 2023 action-plan PDF returned 404, and DOT pages returned 403 to automated fetch.
7. **Gap:** Exact solve times of commercial tools (NetLine xOPT, CAE, IBS). Vendors publish none.
8. **Gap:** The 2024 CODA annual figure; the WASG chapter text on disruption-related slot non-use (justified non-utilisation); the current FAA order number for GDP/SCS procedures.
9. **Gap:** Numerical results of the RL papers (Ding et al. 2023) and of Hizir et al. 2026. Only abstracts were reached.
10. **Gap:** Evidence of LLM/agentic AI in production OCC recovery. Only vendor statements were found (Lufthansa Systems aiOCC, Jeppesen ForeFlight).
11. **Question:** How should passenger-inconvenience cost be calibrated beyond legal compensation (loyalty and churn)? Links to the prioritisation note (§15.7.4).

---

## 10. Sources

| ID | Tier | Title | Publisher / author | Publication date | URL | Accessed | What it supports |
|---|---|---|---|---|---|---|---|
| S-N01 | 1 | CODA Digest Annual Report 2023 | EUROCONTROL (CODA / Aviation Intelligence Unit) | Approved Dec 2024 | https://www.eurocontrol.int/sites/default/files/2024-12/eurocontrol-coda-digest-annual-report-2023.pdf | 2026-11-20 | 46% reactionary share, 8.1 min/flight, codes 91–96, schedule padding |
| S-N02 | 1 | DOT Penalizes Southwest Airlines $140 Million for 2022 Holiday Meltdown | US DOT (press release; also consent order 2023-12-11) | 2023-12-18 | https://www.transportation.gov/briefing-room/dot-penalizes-southwest-airlines-140-million-2022-holiday-meltdown | 2026-11-20 (403 to automated fetch; content via S-N03 and search) | Penalty structure, findings |
| S-N03 | 4 | Southwest will pay a $140 million fine for its meltdown during the 2022 holidays | NPR | 2023-12-18 | https://www.npr.org/2023/12/18/1219906471/southwest-airlines-2022-meltdown-fined-faa | 2026-11-20 | 16,900 cancellations, >2 M pax, $35 M / $90 M / $72 M, >$750 M total |
| S-N04 | 4 | Southwest explains its meltdown to Congress | KSL (AP) | 2023-02-09 | https://www.ksl.com/article/50575686/southwest-explains-its-meltdown-to-congress | 2026-11-20 | Watterson testimony quote; SWAPA claims (500 repositioning flights, 10,000 deadheading pilots) |
| S-N05 | 4 | A top airline executive explains the Southwest Airlines meltdown | View from the Wing (G. Leff, quoting M. St. George) | 2022-12-28 | https://viewfromthewing.com/a-top-airline-executive-explains-the-southwest-airlines-meltdown/ | 2026-11-20 | Nodal network, crew bases, cancel-early argument (opinion) |
| S-N07 | 4 | 2022 Southwest Airlines scheduling crisis | Wikipedia | living page | https://en.wikipedia.org/wiki/2022_Southwest_Airlines_scheduling_crisis | 2026-11-20 (via search) | SkySolver/Crew Web Access described as in-house (conflicting) |
| S-N08 | 4 | 2024 Delta Air Lines disruption | Wikipedia | living page | https://en.wikipedia.org/wiki/2024_Delta_Air_Lines_disruption | 2026-11-20 (via search) | >7,000 cancellations, 1.3–1.4 M pax, dates, DOT "controllable" |
| S-N09 | 4 | Delta says chaos after CrowdStrike outage cost it $550 million | NBC News (reporting Delta SEC 8-K) | 2024-08-08 | https://www.nbcnews.com/business/business-news/delta-says-chaos-crowdstrike-outage-cost-550-million-rcna165864 | 2026-11-20 (via search) | $380 M revenue + $170 M expense, $50 M fuel offset |
| S-N10 | 4 | US closes probe into 2024 Delta Air Lines meltdown | iTnews (Reuters) | 2026-06 | https://www.itnews.com.au/news/us-closes-probe-into-2024-delta-air-lines-meltdown-626681 | 2026-11-20 (via search) | Probe closed without penalty; date conflict |
| S-N11 | 4 | Delta faces federal investigation as it scraps hundreds of flights | CBS News | 2024-07-23 | https://cbsnews.com/news/delta-flight-cancellations-today-dot-investigation-crowdstrike-outage | 2026-11-20 (via search) | Bastian crew-tracking quote; DOT probe opened |
| S-N12 | 1 | 14 CFR Part 117, Table B – FDP: Unaugmented Operations | US Govt (Cornell LII copy of eCFR) | current | https://www.law.cornell.edu/cfr/text/14/appendix-Table_B_to_part_117 | 2026-11-20 | FDP limits 9–14 h |
| S-N13 | 1 | 14 CFR 117.19 Flight duty period extensions | US Govt (Cornell LII) | current | https://www.law.cornell.edu/cfr/text/14/117.19 | 2026-11-20 | Extension rules and reporting |
| S-N14 | 1 | 14 CFR 117.23 Cumulative limitations | US Govt (Cornell LII) | current | https://www.law.cornell.edu/cfr/text/14/117.23 | 2026-11-20 | 100/672, 1,000/365, 60/168, 190/672 |
| S-N15 | 1 | 14 CFR 117.25 Rest period | US Govt (Cornell LII) | current | https://www.law.cornell.edu/cfr/text/14/117.25 | 2026-11-20 | 10 h / 8 h sleep, 30 h in 168 h, 56 h |
| S-N16 | 1 | Flight Attendant Duty Period Limitations and Rest Requirements (final rule, 87 FR 61452) | FAA / Federal Register | 2022-10-12 | https://www.govinfo.gov/content/pkg/FR-2022-10-12/html/2022-21963.htm | 2026-11-20 (via search) | 121.467: 10 h rest, 14 h duty |
| S-N17 | 1 | ORO.FTL.205 Flight duty period (Reg. (EU) 965/2012) | UK CAA Regulatory Library (copy of EU rule) | consolidated, date not shown | https://regulatorylibrary.caa.co.uk/965-2012/Content/Document%20Structure/03%20ORO/2%20Regs/05130_ORO.FTL.205_Flight_duty_period_FDP.htm | 2026-11-20 | 13:00 basic FDP, extensions, commander's discretion |
| S-N18 | 1 | ORO.FTL.235 Rest periods | UK CAA Regulatory Library | consolidated | https://regulatorylibrary.caa.co.uk/965-2012/Content/Document%20Structure/03%20ORO/2%20Regs/05190_ORO.FTL.235_Rest_periods.htm | 2026-11-20 | 12 h / 10 h rest, 36 h recovery |
| S-N19 | 1 | Extended FAQ on Airport Slots | IATA | n.d. | https://www.iata.org/contentassets/c1d7626d7175462ab0fc527c9e2937ce/extended-faq-on-airport-slots.pdf | 2026-11-20 (via search) | 80/20 rule, historic precedence (WASG) |
| S-N20 | 1 | Calculated Take Off Time (CTOT) | SKYbrary (EUROCONTROL-backed) | n.d. | https://skybrary.aero/articles/calculated-take-time-ctot | 2026-11-20 (via search) | CTOT −5/+10; swap limits (from EUROCONTROL networker guide in same search) |
| S-N21 | 1 | Commission Regulation (EU) No 255/2010 (ATFM) | European Commission / EUR-Lex | 2010-03-25 | https://eur-lex.europa.eu/eli/reg/2010/255/oj/eng | 2026-11-20 (via search) | ATFM departure slot definition |
| S-N22 | 1 | Ch. 18 Traffic Management, Section 10 (Ground Delay Programs) | FAA ATC publications | current | https://www.faa.gov/air_traffic/publications/atpubs/foa_html/chap18_section_10.html | 2026-11-20 (via search) | GDP, EDCT, Slot Credit Substitution (order number [VALIDATE]) |
| S-N23 | 1 | Sydney Airport curfew overview | Australian Govt, Dept of Infrastructure | n.d. | https://www.infrastructure.gov.au/infrastructure-transport-vehicles/aviation/aviation-safety/aircraft-noise/airport-curfews/sydney/overview | 2026-11-20 (via search) | 23:00–06:00 curfew, dispensations, fines |
| S-N24 | 4 | Night flying restrictions | Wikipedia | living page | https://en.wikipedia.org/wiki/Night_flying_restrictions | 2026-11-20 (via search) | Frankfurt 23:00–05:00 ban (2011) [VALIDATE] |
| S-N25 | 3 | Disruption management in the airline industry – concepts, models and methods | Clausen, Larsen, Larsen, Rezanova; Computers & OR 37(5):809–821 | 2010 | https://orbit.dtu.dk/en/publications/disruption-management-in-the-airline-industry-concepts-models-and/ | 2026-11-20 (via search) | Foundational survey (aircraft, crew, pax, integrated) |
| S-N26 | 3 | Airline disruption management: A literature review and practical challenges | Hassan, Santos, Vink; Computers & OR 127 | 2021 | https://research.tudelft.nl/en/publications/airline-disruption-management-a-literature-review-and-practical-c | 2026-11-20 (via search) | 2009–2018 review; growth of integrated models; AOCC gap |
| S-N27 | 3 | Airline disruption management—Perspectives, experiences and outlook | Kohl, Larsen, Larsen, Ross, Tiourine; JATM 13(3):149–162 | 2007 | https://ideas.repec.org/a/eee/jaitra/v13y2007i3p149-162.html | 2026-11-20 (via search) | Practitioner perspective; R&D project (background) |
| S-N28 | 3 | An optimization approach to airline integrated recovery | Petersen, Sölveling, Clarke, Johnson, Shebalov; Transportation Science 46(4):482–500 | 2012 | https://ideas.repec.org/a/inm/ortrsc/v46y2012i4p482-500.html | 2026-11-20 (via search) | Integrated beats sequential; acceptable time |
| S-N29 | 3 | Flight operations recovery: New approaches considering passenger recovery | Bratu & Barnhart; J. Scheduling 9(3):279–298 | 2006 | https://dspace.mit.edu/entities/publication/3308d708-6290-4f28-81b4-a3ad7de44605 | 2026-11-20 (via search) | Passenger-cost-aware recovery |
| S-N30 | 3 | Analysis of the potential for delay propagation in passenger airline networks | AhmadBeygi, Cohn, Guan, Belobaba; JATM 14(5):221–236 | 2008 | https://ideas.repec.org/a/eee/jaitra/v14y2008i5p221-236.html | 2026-11-20 (via search) | Slack vs propagation; hub vs P2P carriers |
| S-N31 | 3 (airline-specific) | Decision Support for Schedule Recovery at Lufthansa Group Airlines | Davies et al. (Google Research, SWISS, Lufthansa); INFORMS J. Applied Analytics 56(1):58–75, doi 10.1287/inte.2025.0296 | Jan–Feb 2026 | https://www.business.uzh.ch/dam/jcr:d5051dd1-ce0f-4104-9f4b-5c9603ea6c65/davies-et-al-2026-decision-support-for-schedule-recovery-at-lufthansa-group-airlines.pdf | 2026-11-20 (full text read) | OPSD methods, data effort, adoption metrics, savings, timing |
| S-N32 | 3 | Disruption Management in Airline Operations: A Solver-based Approach using Time-Space Network Optimization | Rodrigues et al.; arXiv 2510.26831 (preprint) | 2025-10-29 | https://arxiv.org/html/2510.26831v1 | 2026-11-20 | Method survey; ~10 min solve target; adoption barriers |
| S-N33 | 3 | Large-Scale Airline Crew Recovery Using Mixed-Integer Optimization and Supervised Machine Learning | Hizir, Barnhart, Vaze; Transportation Science 60(2):177–196 | 2026-03 | https://pubsonline.informs.org/doi/10.1287/trsc.2025.0105 | 2026-11-20 (abstract via search) | ML+MIP hybrid; >2,800 daily flights; tens of millions savings (estimated) |
| S-N34 | 3 | Towards efficient airline disruption recovery with reinforcement learning | Ding, Wandelt, Wu, Xu, Sun; Transp. Res. Part E 179:103295 | 2023-11 | https://www.econbiz.de/Record/towards-efficient-airline-disruption-recovery-with-reinforcement-learning/10014487495 | 2026-11-20 (abstract via search) | DRL + VNS hybrid |
| S-N35 | 3 | Aircraft swapping with reinforcement learning (Hondet et al., SID 2018) | ENAC / HAL | 2018 | https://hal-enac.archives-ouvertes.fr/hal-01944612 | 2026-11-20 (via search summary) | Pure RL "far from optimal" |
| S-N36 | 2 | NetLine/Ops ++ Optimizer Suite – Solver xOPT / Tail xOPT (product brochure) | Lufthansa Systems | ~2020-11 (CDN path) | https://cdn.lhsystems.com/2020-11/pb_netline_opssolver_tail.pdf | 2026-11-20 (full text read) | Recovery levers, constraints, scenario features |
| S-N37 | 2 | NetLine/Ops ++ aiOCC | Lufthansa Systems | 2022 (product info) | https://www.lhsystems.com/solutions/ai-other-services/netlineops-aiocc | 2026-11-20 (via search) | Recommendation-only; decision stays with controller |
| S-N38 | 2 | Operations Control (brochure) | CAE | n.d. | https://www.cae.com/media/documents/Civil_Aviation/Brochures/Operations_Control.pdf | 2026-11-20 (via search) | Movement Manager, Recovery Manager Ops, cost-aware recovery |
| S-N39 | 2 | CAE Inc. Form 40-F FY2022 (MD&A) | CAE / SEC | 2022 | https://www.sec.gov/Archives/edgar/data/1173382/000117338222000017/cae_033122xex3mda.htm | 2026-11-20 (via search) | AirCentre acquisition, 28 Feb 2022 |
| S-N40 | 2 | Jeppesen ForeFlight launches as a standalone company | Thoma Bravo | 2025 | https://www.thomabravo.com/press-releases/jeppesen-foreflight-launches-as-a-standalone-company-to-redefine-the-future-of-aviation-software | 2026-11-20 (via search) | Ownership change; crew tracking continuity |
| S-N41 | 2/4 | British Airways taps IBS Software for ops management | Runway Girl Network (IBS press release) | 2018-06-21 | https://runwaygirlnetwork.com/2018/06/21/press-release-british-airways-taps-ibs-software-for-ops-management | 2026-11-20 (via search) | iFlight NEO at BA; iFlight scope |
| S-N42 | 2 | Amadeus Passenger Recovery | Amadeus | n.d. | https://amadeus.com/en/portfolio/airlines/passenger-recovery | 2026-11-20 (via search) | Automated rebooking incl. other carriers; prioritisation |
| S-N43 | 2 | How Amadeus helps Air Canada rebook disrupted passengers in just 10 minutes | Amadeus blog | n.d. | https://amadeus.com/en/blog/articles/how-amadeus-helps-air-canada-rebook-disrupted-passengers-in-just-10-minutes | 2026-11-20 (via search) | ~90% automated, 10 min vs 12 h (vendor-reported) |
| S-N44 | 2 | Network Operations Optimization (datasheet) | GE Aerospace | undated | https://www.geaerospace.com/sites/default/files/networkoperations_optimization.pdf | 2026-11-20 (full text read) | 72+ h impact horizon; $25 bn / $281 claim (uncited) |
| S-N45 | 2 | Airline Disruption Management (whitepaper) | T2RL (I. Gershkoff) for Amadeus | 2016-09 | https://amadeus.com/documents/en/blog/pdf/2016/09/airline-disruption-management-whitepaper-2016.pdf | 2026-11-20 (full text read) | Cost estimates; repair domains; interactive tool preference |
| S-N46 | 2 | Shaping the future of Airline Disruption Management (IROPS) | T2RL for Amadeus | 2016 | https://amadeus.com/documents/en/airlines/white-paper/shaping-the-future-of-airline-disruption-management.pdf | 2026-11-20 (full text read) | 8% / $60 bn claim (conflict); 70 min pax recovery example |
| S-N47 | 1 (airline official; claims unverified) | Meet HEAT: American's tool to manage through summer storms | American Airlines Newsroom | 2023-07-06 | https://news.aa.com/news/news-details/2023/Meet-HEAT-Americans-tool-to-manage-through-summer-storms-OPS-OTH-07/default.aspx | 2026-11-20 | HEAT inputs, usage, ~1,000 cancellations avoided |
| S-N48 | 1/3 | Total Delay Impact Study | Ball et al. (NEXTOR, for FAA) | 2010-10 (rev. 2010-12) | https://rosap.ntl.bts.gov/view/dot/6234 | 2026-11-20 (via search) | $32.9 bn (2007 US); $8.3 bn airlines |
| S-N49 | 1 | Regulation (EC) No 261/2004 (Arts 5, 7, 8) | European Parliament & Council | 2004-02-11 | https://eur-lex.europa.eu/eli/reg/2004/261/oj | 2026-11-20 (content via legislation.gov.uk copy in search) | Re-routing, notice thresholds, compensation |
| S-N50 | 1 | Refunds and Other Consumer Protections (final rule) | US DOT / Federal Register 2024-07177 | 2024-04-26 | https://www.federalregister.gov/documents/2024/04/26/2024-07177/refunds-and-other-consumer-protections | 2026-11-20 (via search) | 3 h / 6 h significant change; automatic refunds |
| S-N51 | 1 | Guidance document – Interline considerations on IROPS | IATA | 2020-06-25 | https://www.iata.org/contentassets/e7a533819be440edbb1e49da96e0f2a8/guidance-document-interline-irops_25june2020.pdf | 2026-11-20 (via search) | Res. 735d scope, FIM last resort |
| S-N52 | 1 | Standard Schedules Information Manual (SSIM) | IATA | 36th ed. 2026 | https://www.iata.org/ssim | 2026-11-20 (via search) | SSM (Ch. 4), ASM (Ch. 5) |
| S-N53 | 1 | IATA delay codes (definition) | EUROCONTROL Performance Review Unit (ansperformance.eu) | n.d. | https://www.ansperformance.eu/definition/iata-delay-codes/ | 2026-11-20 (via search) | AHM 730 codes; AHM 780 MVT |
| S-N54 | 1 | A-CDM Milestones Approach (workshop slides) | ICAO MID (EUROCONTROL A-CDM concept) | 2023 | https://www.icao.int/MID/Documents/2023/ACDM/PPT_5%20-%20ACDM%20Milestones%20approach.pdf | 2026-11-20 (via search) | A-CDM milestones, TOBT/TSAT, DPI |
| S-N55 | 1 | 14 CFR 121.628 Inoperable instruments and equipment | US Govt (Cornell LII) | current | https://www.law.cornell.edu/cfr/text/14/121.628 | 2026-11-20 | MEL dispatch rules |

*"via search" means the content was confirmed through search-result extracts rather than a full-page read; these entries should be re-read before reuse in a product deliverable.*
