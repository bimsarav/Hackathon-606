# 01 — Flight Disruption Prediction (MASTER_PROMPT §15.7.1)

> Research question: *How can AI help an airline predict, assess and minimise the impact of flight disruptions on its network and passengers?* This note covers the **prediction** layer: delays, cancellations, technical, weather, ATC/ATFM, crew and rotation risk, and predictive monitoring of upcoming flights.
> Researched 2026-11-20.
> Labels: `[STD]` standard/regulation · `[PRACTICE]` common industry practice · `[SPECIFIC]` one airline/vendor · `[ACADEMIC]` research · `[AI-OPP]` potential AI improvement · `[VALIDATE]` to confirm with an airline or primary document.
> Related notes (same folder): [00-OVERVIEW](00-OVERVIEW.md) · [01 prediction](01-disruption-prediction.md) · [02 network impact & recovery](02-network-impact-and-recovery.md) · [03 passenger impact](03-passenger-impact.md) · [04 prioritisation & rights](04-passenger-prioritization-and-rights.md) · [05 OCC/PCU & systems](05-occ-pcu-workflows-and-systems.md). Sources: [`../../SOURCES.md`](../../SOURCES.md) (IDs are namespaced per note and final; no renumbering). Glossary: [`../../GLOSSARY.md`](../../GLOSSARY.md).

---

## 1. Key findings

- **Reactionary (knock-on) delay is the single largest delay category in Europe, so predicting propagation matters as much as predicting the first delay.** [STD/PRACTICE] EUROCONTROL CODA reports reactionary delay at 46% of delay minutes in 2024 (8.0 min/flight) [S-P02], and 7.1 of 15.0 min average departure delay per flight in September 2026 [S-P01]. The 2024 figure comes from a digest whose status line reads "Working Draft", so check it against the final edition [VALIDATE].
- **Protecting the first wave pays off over the whole day.** [PRACTICE] EUROCONTROL found that a 0.9 min/flight first-wave improvement in 2025 went with a 2.8 min/flight all-day improvement and a cumulative 6.3 min/flight lower delay by 22:00 UTC [S-P03]. Early-day signals, such as night-stop aircraft readiness, crew sign-on and the first-rotation TOBT, are high-value prediction targets [AI-OPP].
- **The best-proven "AI in disruption" deployments are in technical reliability (predictive maintenance) and in recovery optimisation. Generic network-wide delay prediction is less proven.** [SPECIFIC] Examples:
  - Delta reports maintenance cancellations fell from more than 5,600 in 2010 to 55 in 2018, and a >95% success rate for pending-failure predictions. This is company-reported and the cause is not isolated [S-P27].
  - easyJet avoided 44 cancellations in July 2024 and 35 in August 2024 with Skywise predictive maintenance (Airbus-reported) [S-P25].
  - Lufthansa Group's OPSD recovery optimiser is in daily use at SWISS: CHF 8.5 M in savings by Jan 2025, and 26% of all controller changes came from solver suggestions [S-P31]. It is **optimisation, not ML prediction**.
- **Accuracy depends strongly on the prediction horizon, and published figures are not comparable.**
  - [ACADEMIC] Random-forest network-state models: 19% classification error (above/below 60 min) at a 2-hour horizon, and a 21-minute median regression error on the 100 most-delayed US links [S-P40].
  - [ACADEMIC] EUROCONTROL/MUAC ML take-off-time prediction at EOBT-1h: about 30% less error than ETFMS [S-P36].
  - [SPECIFIC] Vendor ETA claims, such as FlightAware's "30–50% more accurate", are not independently benchmarked [S-P35].
  - Most academic accuracy claims use public US BTS data, with different thresholds, horizons and leakage controls [S-P41][S-P42].
- **Most of the "cause" of a delay is fixed by external, rule-based processes that already publish strong signals.** [STD] ATFM regulations give a CTOT with a −5/+10 min tolerance [S-P13][S-P14]. FAA Ground Delay Programs give EDCTs, and Ground Stops hold departures [S-P10][S-P11]. Once a CTOT or EDCT exists, the delay at take-off is largely *known*. The value of AI is in **anticipating** regulations, programs and their downstream effects before they are issued (e.g. D-1 ATFM delay prediction [S-P39]), and in turning the known delay into network and passenger impact [AI-OPP].
- **Delay-cause data is noisy and not harmonised.** [STD/PRACTICE]
  - IATA codes: AHM 730/731, with AHM 732 now the reference schema in AIDX [S-P04][S-P05][S-P06].
  - BTS uses five cause buckets that apply only to arrival delays of 15 minutes or more [S-P07][S-P08], and a 2026 DOT proposal would change the "Air Carrier" definition [S-P09].
  - CODA counts delay from 1 minute, groups codes 90–96 as reactionary, and its monthly coverage can be partial (57.1% of IFR flights, Sep 2026) [S-P01].
  - Training labels must therefore be treated as approximate [VALIDATE].
- **Predictions help only if they arrive before the decision deadline.** [PRACTICE] Lufthansa/SWISS: "we cannot rebook passengers on a flight departing in 30 minutes if making that decision requires 45 minutes" [S-P31]. Typical decision windows:
  - Pre-tactical (D-1): spare aircraft, crew reserves, pre-emptive cancellations.
  - EOBT-3h to EOBT-40min: A-CDM DPI messages to the Network Manager [S-P16].
  - Several hours before departure: United ConnectionSaver hold recommendations [S-P33].
  - After the CTOT/EDCT is issued: mostly slot swaps and passenger re-protection.

## 2. Domain fundamentals & terminology

| Term | Meaning | Source |
|---|---|---|
| OTP15 / on-time | **US DOT/BTS:** on time = arrival (gate-in, parking brake set) less than 15 min after the scheduled time; departure on time if it leaves the gate less than 15 min after schedule [STD]. **EUROCONTROL:** reports OTP15 and also a ±5 min threshold [PRACTICE]. | [S-P07][S-P08][S-P01][S-P03] |
| Primary delay | A delay caused at the flight's own departure station or in its own processes (airline, airport, ATFM, weather, government), not inherited from a previous flight. | [S-P01][S-P04] |
| Reactionary delay | A delay inherited from an earlier flight: late inbound aircraft, waiting crew, waiting load or connecting passengers, or an operations-control decision. IATA codes 91–96. CODA groups them as "90–96" (conflict noted in §8). | [S-P04][S-P01] |
| IATA delay codes (AHM 730) | Standard two-digit numeric (and two-letter alpha) delay reasons, grouped by category (see the code groups below). AHM 780 recommends numeric codes in movement messages. | [S-P04][S-P06] |
| AHM 731 / AHM 732 | **AHM 731:** IATA delay sub-codes, listed in a CODA annex. **AHM 732:** the newer delay-code schema with a "process matrix" (webinar dated 3 Mar 2023). The AIDX guide v22.1 points ReasonCode to AHM 732. The adoption level per airline is unknown [VALIDATE]. | [S-P05][S-P06] |
| BTS cause categories | Air Carrier, Extreme Weather, National Aviation System (NAS), Security, Late-Arriving Aircraft. Reported only for arrival delays of 15 min or more. | [S-P07][S-P08] |
| CODA | EUROCONTROL Central Office for Delay Analysis. Collects airline-reported delay causes and publishes monthly/annual digests. Delay is counted from 1 minute. | [S-P01][S-P02] |
| ATFM / ATFCM regulation | Network Manager measure that limits flow through a sector or airport when demand exceeds capacity. Flights affected receive a slot. | [S-P13][S-P14] |
| CTOT (ATFM slot) | Calculated Take-Off Time, issued centrally by the Network Manager (formerly CFMU). Tolerance −5/+10 min. EU 255/2010 requires slot-adherence monitoring (target ≥80% compliance). | [S-P13][S-P14] |
| A-CDM: EOBT / TOBT / TSAT / TTOT | EOBT = Estimated Off-Block Time (flight plan). TOBT = Target Off-Block Time (airline/handler). TSAT = Target Start-up Approval Time (ATC, derived from TTOT). TTOT = Target Take-Off Time. | [S-P16][S-P17] |
| DPI | Departure Planning Information. Messages from A-CDM airports to the Network Manager: E-DPI from EOBT-3h to EOBT-2h, T-DPI-t from EOBT-2h to EOBT-40min, then T-DPI-s, A-DPI, C-DPI. An update is sent when TOBT or TSAT changes by 5 min or more. | [S-P16] |
| DLA | Delay message to update the flight plan EOBT. One airport guide requires it when TOBT is more than 15 min beyond EOBT. | [S-P17] |
| GDP (FAA) | Ground Delay Program. ATCSCC assigns arrival slots and holds aircraft on the ground at their origin when demand at an airport exceeds the acceptance rate for an extended period. | [S-P10][S-P11][S-P12] |
| EDCT (FAA) | Expect Departure Clearance Time, issued under a GDP. | [S-P10][S-P12] |
| Ground Stop (FAA) | Departures to the affected airport are held at origin. Short-term; often replaced by a GDP when the duration is unclear. | [S-P10][S-P12] |
| ATCSCC | FAA Air Traffic Control System Command Center (Warrenton, VA). Issues GDP and GS advisories. | [S-P10] |
| METAR / TAF / SIGMET | **METAR:** routine aerodrome weather observation. **TAF:** aerodrome forecast; Annex 3 Amendment 74 (2008) recommends 6–30 h validity, and 30-h TAFs are common at major aerodromes, but older texts say 9–24 h (conflict, §8). **SIGMET:** en-route significant-weather warning. Current Annex 3 text not checked [VALIDATE]. | [S-P22][S-P23] |
| HOT | Holdover time: how long de/anti-icing fluid protects the aircraft. The FAA publishes guidelines every year; the Winter 2026–27 edition is dated 11 Aug 2026. Part 121 carriers need an approved ground de-icing programme (14 CFR 121.629(c)). | [S-P24] |
| AOG | Aircraft on Ground: the aircraft cannot fly until it is fixed. The main technical driver of cancellations. | [S-P25][S-P27] |
| Predictive maintenance / health monitoring | Uses aircraft sensor and fault data to predict component failures, so that unscheduled removals become scheduled work (Skywise, Boeing AHM). | [S-P25][S-P28] |
| POBT | Predicted Off-Block Time. Vendor ML term (Assaia), described as better than A-CDM TOBT (vendor claim). | [S-P47] |

**IATA delay-code groups (AHM 730)** [STD] [S-P04]:

| Codes | Category |
|---|---|
| 00–09 | Others (00–05 are airline-internal) |
| 11–19 | Passenger and baggage |
| 21–29 | Cargo and mail |
| 31–39 | Aircraft and ramp handling |
| 41–48 | Technical and aircraft equipment |
| 51–58 | Damage and EDP failure |
| 61–69 | Flight operations and crewing |
| 71–77 | Weather |
| 81–84 | ATFM restrictions |
| 85–89 | Airport and governmental authorities |
| 91–96 | Reactionary |
| 97–99 | Miscellaneous |

**Codes most relevant to prediction** [STD] [S-P04]:

| Code | Meaning |
|---|---|
| 81 AT | En-route demand/capacity |
| 82 AX | En-route staffing, equipment or industrial action |
| 83 AE | Destination restriction |
| 84 AW | Destination weather (ATFM) |
| 87 AF | Airport facilities |
| 89 AM | Departure airport restriction (weather goes here only under an ATFM regulation; otherwise use 71) |
| 91 RL | Load from another flight |
| 92 RT | Through check-in error |
| 93 RA | Late inbound aircraft |
| 94 RS | Cabin crew from another flight |
| 95 RC | Flight-deck or whole crew from another flight |
| 96 RO | Operations-control decision (reroute, diversion, consolidation, non-technical aircraft change) |

## 3. Processes, decisions & timing

Who uses predictions, what they decide, and when. The phases follow the strategic → pre-tactical → tactical → post-ops convention used by EUROCONTROL [S-P39][S-P15]. Mapping each decision to an exact airline role needs validation [VALIDATE].

| Phase / horizon | User (typical) | Decision a prediction supports | Prediction needed | Too late when… |
|---|---|---|---|---|
| **Strategic** (weeks to months; schedule build) | Network planning, scheduling | Block-time buffers, turn times, minimum connecting times by station and season, bank structure | Delay *distributions* by route, time of day and season [S-P45] | The schedule is published and sold |
| **Seasonal / D-7 to D-2** | Maintenance control, crew planning | Plan predicted component removals into scheduled checks; size crew reserves and standby | Component failure risk [S-P25][S-P27]; disruption-risk days (storms, strikes, ATC staffing) [AI-OPP] | The aircraft is AOG away from base with no spare part |
| **Pre-tactical D-1** | OCC / network control, NM liaison, crew control | Pre-emptive cancellations before a storm or strike (cancel early, re-accommodate in an orderly way); swap aircraft so that robust tails fly the long rotations; position spares; request reroutes | Flights likely to be ATFM-regulated and their delay [S-P39]; weather impact; next-day tail assignment risk (SWISS: "one full controller shift per day" was spent preparing the next day's tail assignment before OPSD [S-P31]) | NM publishes regulations and slots on the day |
| **Day of operations: EOBT-3h to EOBT-40min** | OCC duty manager, hub control centre, A-CDM partners | Update TOBT / send DLA; improve or swap CTOTs between own flights in the same regulation (requests are reviewed by NMOC, not guaranteed) [S-P13]; tail swaps; crew re-pairing; connection protection | Take-off time / TOBT prediction [S-P36][S-P37]; inbound ETA [S-P38][S-P35]; reactionary chain; crew legality breaches | CTOT/EDCT issued, boarding started, crew out of hours |
| **Hours before departure (connections)** | Hub connection planners, gate agents | Hold or don't hold an outbound flight for late connecting passengers (United ConnectionSaver starts "several hours before departure"; gate agents see a hold/no-hold recommendation) [S-P33] | Inbound gate-arrival ETA and passenger walk time [S-P33] | The outbound door is closed |
| **Turnaround (minutes)** | Station/ramp control, airport operations | Re-sequence ground resources; update TOBT | POBT from video and events (vendor) [S-P47] | Off-block |
| **Post-operations** | Performance, OCC lessons learned, finance | Delay-code allocation, EU261 defence (extraordinary circumstances), model retraining | Cause attribution | — |

**Operational notes**
- **A decision that cannot be executed in time has no value.** [PRACTICE] Recovery decisions must often be taken "within minutes"; a fast, acceptable solution is preferred to an optimal one that takes hours [S-P31].
- **Humans make the final call.** [PRACTICE] Every production case found keeps a human decision-maker:
  - SWISS controllers accept or modify the scenarios OPSD proposes [S-P31].
  - Delta's 2020 OCC platform produces "hypothetical outcomes that help Delta's professionals make critical decisions" [S-P29][S-P30].
  - ConnectionSaver produces a recommendation to gate agents [S-P33].
  - Cancellation lists are reviewed by dispatch and OCC staff before release; this comes from a Tier-4 press source and still needs validation [VALIDATE].
- **External programs override airline intent.** [STD]
  - A FAA Ground Stop overrides other traffic management initiatives, and a flight cannot be released without approval from the issuing facility [S-P10].
  - Under an ATFM regulation, the departure window shrinks from the normal ±15 min around EOBT to −5/+10 min around the CTOT [S-P13][S-P14 via search summary].

## 4. Data requirements

| Data | Origin system / provider | Update frequency | Standard / format | Notes |
|---|---|---|---|---|
| Schedule (planned legs, tails, rotations) | Airline scheduling / OCC system | Seasonal; daily changes | SSIM / SSM / ASM (IATA) — standard names known, not checked in this pass [VALIDATE] | Needed for rotation and crew-link features |
| Movement events (OUT/OFF/ON/IN), delay codes | Airline DCS/OCC, ground handlers; ACARS OOOI | Event-driven (seconds to minutes) | IATA AHM 780 MVT messages with AHM 730/732 codes; AIDX XML (ReasonCode → AHM 732) [S-P06][S-P04] | Labels for training; delay-code quality varies (§8) |
| Flight plan & ATFM status (EOBT, CTOT, regulations, ETFMS estimates) | EUROCONTROL Network Manager (ETFMS); NM B2B services | Real time | ICAO flight plan; NM slot messages (SAM/SRM/SLC — names not checked in source) [VALIDATE]; NM B2B web services [VALIDATE] | The ETFMS take-off estimate is the baseline that ML improved by about 30% [S-P36] |
| A-CDM milestones (TOBT, TSAT, TTOT, DPI) | Airport A-CDM platform ↔ NM | Event-driven; update when ≥5 min change | EUROCONTROL DPI Implementation Guide (ed. 2.7, Jun 2025 — listed but not read) [S-P16][VALIDATE] | Only at A-CDM airports |
| US traffic management (GDP, GS, EDCT, airport acceptance rates) | FAA ATCSCC / TFMS; NAS Status; OIS advisories | Real time | FAA advisories; SWIM feeds [VALIDATE format] | [S-P10][S-P11] |
| Weather observations & forecasts | National met services (ICAO Annex 3 / WMO) | METAR routinely (often half-hourly/hourly) [VALIDATE]; TAF every 3 or 6 h depending on validity [S-P22]; SIGMET on event | METAR/TAF/SIGMET (TAC; IWXXM XML is the ICAO digital form [VALIDATE]) | Convective nowcasts and ensembles are needed beyond TAF [AI-OPP] |
| De-icing conditions & HOTs | Station de-icing; FAA/Transport Canada HOT tables | Annual tables; event-driven operations | FAA HOT Guidelines; DSHOT snow database [S-P24] | De-icing throughput is a capacity constraint at hubs |
| Aircraft health (fault messages, sensor parameters, MEL items, deferred defects) | Aircraft (ACMS/CMS via ACARS/Wi-Fi); OEM platforms (Airbus Skywise, Boeing AHM); airline M&E system | Real time in flight + post-flight downloads | OEM-specific; MEL per operator | Skywise monitors 180+ airframe/system items on an A320 [S-P25]; Boeing AHM: 4.2 M conditions evaluated daily (vendor) [S-P28] |
| Crew rosters, legality, sign-on status | Crew management system (e.g. pairings, rosters, FTL rules) | Real time on the day | Airline-specific; FTL regulation (EASA ORO.FTL / FAA Part 117) [VALIDATE] | Needed for codes 94/95 risk; drove the Southwest Dec 2022 cascade (press) [S-P49] |
| Passenger connections | PSS/DCS (PNR, through check-in) | Real time | PNR/PNL/PTM [VALIDATE] | Turns flight delay into passenger impact (§15.7.3) |
| Public historical on-time data | US BTS (Reporting Carrier On-Time Performance) | Monthly | CSV; 14 CFR Part 234 reporting [S-P07][S-P08] | Only reporting US carriers; cause buckets are coarse |
| FAA ASPM | FAA | Daily/monthly | Web/DBF; **login required** | Covers ASPM airports (77 cited) and ASPM carriers; **operated flights only, no cancellations**; inputs include ARINC OOOI, ETMS and ASQP [S-P18] |
| EUROCONTROL research data | Aviation Data Repository for Research (ADRR) via OneSky Online | About 3 M flights added per year (about 28 M as of Jul 2026) | Free; R&D-only; no redistribution | Commercial flights only [S-P19] |
| EUROCONTROL performance data | CODA digests, PRU/ANS Performance dashboards | Monthly/annual | PDF/dashboards | Aggregated, not per flight [S-P01][S-P04] |
| ADS-B trajectories | OpenSky Network (crowd-sourced) | Real time; historical via Trino (application needed) | ADS-B / Mode S, SQL (Trino) | Weak coverage over oceans and remote areas; ADS-C being added [S-P20][S-P21] |
| Commercial flight-status and ETA feeds | FlightAware, Cirium, OAG and others (vendors) | Real time | APIs | Vendor accuracy claims are not independently verified [S-P35] |

## 5. Business rules & constraints

- **[STD] ATFM slot compliance.**
  - The CTOT tolerance is −5/+10 min [S-P13].
  - EU 255/2010 defines the ATFM departure slot and requires states to monitor slot adherence at airports (≥80% compliance target per the search summary of the regulation) [S-P14].
  - Slot extensions and swaps are subject to Network Manager (NMOC) rules and local AIP; for example, the Dutch AIP allows a one-time extension of up to 10 min [S-P14 summary; VALIDATE per state].
- **[STD] FAA programs.** Under a GDP, aircraft are held at origin through EDCTs [S-P10][S-P11].
  - A facility may run a local ground stop of up to 15 min without notifying the ATCSCC, and no facility ground stop may exceed 30 min [S-P10].
  - The ATCSCC must be notified once delay is expected to reach 15 min or more [S-P10].
- **[STD] US DOT reporting.**
  - Reporting carriers submit on-time data under 14 CFR Part 234 [S-P08].
  - Cause codes apply only when the arrival delay is 15 min or more [S-P07].
  - A 2026 DOT proposal would revise what may be counted as "Air Carrier" delay [S-P09]. Its status is not verified [VALIDATE].
- **[STD] Passenger rights shape the economics of prediction (hard constraints, see §15.7.4).**
  - Under EU261 as interpreted in *Sturgeon* (C-402/07, C-432/07, 2009), arrival 3 h or more late gives fixed compensation unless the airline proves extraordinary circumstances [S-P51].
  - Extraordinary circumstances remove compensation but **not** the duty of care [S-P51].
  - A 2026 report says the court held that inherent technical problems are not extraordinary [S-P51 search summary; VALIDATE judgment].
  - Consequence: predicting a technical delay (airline-attributable) is worth more in the EU than predicting an ATC or weather delay, because the airline both pays compensation and has the levers to act [AI-OPP][VALIDATE with the legal team].
- **[STD] De-icing.**
  - Holdover times come from the annual FAA (with Transport Canada and SAE G-12) guidelines [S-P24].
  - Part 121 carriers need an approved ground de-icing programme [S-P24].
  - A prediction cannot shorten a HOT. It can only anticipate de-icing queues and their capacity effects.
- **[STD] Maintenance.**
  - Predictive alerts do not by themselves change airworthiness requirements.
  - Boeing states that AHM is FAA- and EASA-approved for condition-based scheduled maintenance (vendor statement) [S-P28].
  - MEL dispatch rules decide whether a known defect grounds the aircraft [VALIDATE operator MEL].
- **[PRACTICE] Punctuality vs connections trade-off.** EUROCONTROL attributes part of the 2025 first-wave gain to "prioritising punctuality over passenger connections" [S-P03]. Hold rules are a commercial policy that differs by airline. United holds only when the downstream impact is acceptable; about 20% of held flights actually departed late, by an average of 6 min (2019, airline-reported) [S-P33].
- **[PRACTICE] A-CDM discipline.** TOBT must be kept updated. Updates of 5 min or more trigger DPI messages to the Network Manager [S-P16]. A TOBT more than 15 min beyond EOBT requires a DLA (Dublin rule) [S-P17]. These are rule-driven updates that an ML ETA/TOBT could feed [AI-OPP].

## 6. Industry practice & real-world cases

| Case | Who / when | What it does | Reported outcome | Evidence quality | Label |
|---|---|---|---|---|---|
| Delta TechOps predictive maintenance (PRM with Airbus from 2015; Skywise SPM agreement 2018; APEX engines) | Delta, press release 16 Oct 2019 | Predicts pending component failures | Maintenance cancellations from >5,600 (2010) to 55 (2018); >95% success on pending-failure predictions | Company-reported; the share due to predictive maintenance is not isolated | [SPECIFIC] [S-P27] |
| Skywise Fleet Performance+ (Digital Alliance: Airbus, Delta TechOps, GE Aerospace, Liebherr) | Airbus, 22 Oct 2024 | Predicts part/system failures; 180+ items on an A320 | easyJet avoided 44 (Jul 2024) and 35 (Aug 2024) cancellations; about 11,600 aircraft connected to Skywise; SFP+ about 40 customers / 1,500 aircraft | OEM-reported | [SPECIFIC] [S-P25] |
| Skywise Health Monitoring | Airbus (dates vary) | Real-time health monitoring | Emirates "around one percent" operational reliability gain; Cebu Pacific "no less than one aircraft out of service per day" saved | OEM marketing quotes, seen via search summary only | [SPECIFIC][VALIDATE] [S-P26] |
| Boeing Airplane Health Management + Insight Accelerator | Boeing (service about 20 years old) | Real-time alerts, prognostics, custom/AI alerts | >120 airlines, 4,800 aircraft, 4.2 M conditions per day; "$1.2M single-month savings" example | Vendor-reported | [SPECIFIC] [S-P28] |
| Delta OCC ML platform | Delta, CES Jan 2020; live launch planned spring 2020 | Analyses "millions of operational data points" (aircraft positions, crew restrictions, airport conditions) to produce hypothetical outcomes for decisions before and during disruption; post-mortem tool | No published metrics; current status unknown | Press/company | [SPECIFIC][VALIDATE] [S-P29][S-P30] |
| Lufthansa Group OPSD (with Google) | Announced 20 Jan 2020 (SWISS test); INFORMS paper 2026 (Edelman keyword) | Recovery and next-day schedule optimisation with two solvers, decomposition and heuristics; includes a delay-propagation heuristic | CHF 8.5 M + 14.7 kt CO2 saved by Jan 2025 (Schedule Optimizer); 222,714 accepted changes = 26% of controller changes; being rolled out across the Group (paper abstract: EUR 12 M saved, target EUR 30 M per year) | Peer-reviewed practice paper (co-authored by the vendor and the airline) | [SPECIFIC] [S-P31][S-P32] |
| United ConnectionSaver | United, 10 Jun 2019 (DEN, ORD first) | Hold/no-hold recommendations for connections; passenger texts | 14,400 connections saved in 4 months; about 20% of held flights departed late, average 6 min | Airline-reported; the algorithm is not published | [SPECIFIC] [S-P33] |
| Google Flights delay predictions | Google, 31 Jan 2018 | ML on historical status data; flags a delay only at ≥80% confidence | No published accuracy. Press misreported the threshold as "80% accurate" (conflict, §8) | Consumer product; vendor | [SPECIFIC] [S-P34] |
| FlightAware Foresight | FlightAware (ongoing) | ML/neural ETA (landing, gate-in), taxi-out | "30–50% more accurate than conventional methods" (baseline unstated) | Vendor-reported | [SPECIFIC] [S-P35] |
| EUROCONTROL MUAC take-off time ML | Dalmau et al., JATM 2021 | Predicts take-off time; explainable (feature attribution); extended toward flight-plan-filing horizon | About 30% error reduction vs ETFMS at EOBT-1h | Peer-reviewed; operational status in NM not confirmed | [ACADEMIC] [S-P36] |
| EUROCONTROL Innovation Hub turnaround/TOBT probabilistic ML | SIDs 2023 | Probabilistic turnaround and TOBT at four airports | Stated deployment at Prague and Fiumicino in Q1 2024 — **not verified** | Conference paper | [ACADEMIC][VALIDATE] [S-P37] |
| Assaia ApronAI (POBT) | e.g. JFK T4 (JFKIAT), Ljubljana | Computer vision on ramp video → predicted off-block time | JFKIAT: average 5-min reduction in ground delays; vendor report claims AI-monitored turns overrun by 7.3 vs 11.4 min (not a controlled study) | Vendor-reported | [SPECIFIC] [S-P47] |
| NASA Digital Information Platform / ATD-2 surface ML | NASA, DFW/CLT field evaluations (2021–2023) | ML runway, taxi and take-off predictions | Runway prediction accuracy close to ATC assignment; taxi-time uncertainty about 10–15%; airline operational deployment not confirmed | Government R&D | [ACADEMIC] [S-P48] |
| Southwest Dec 2022 meltdown | DOT order Dec 2023; amended Dec 2025 | Winter storm → crew-recovery system overwhelmed (press) → about 16,900 cancellations | $140 M civil penalty. The 2025 amended order cites modernised crew operations, movement control and network-recovery optimisers | Regulator documents + press. The crew-system causation is press-sourced, not a DOT finding | [SPECIFIC] [S-P49][S-P50] |

**Patterns** [PRACTICE]:
- Production systems with published outcomes are almost all **OEM/MRO predictive maintenance** or **optimisation-based recovery and connection tools**.
- Published, audited production results for "flight-level delay probability" models at named airlines were **not found** in this pass. A Lufthansa delay-prediction item found was a TUM student project with Celonis [S-P55].
- Absence of evidence ≠ absence of use: OCC vendors may embed such models [VALIDATE].

## 7. AI/technology approaches

| Approach | Typical data | Horizon | Reported performance (as published) | Status | Limitations |
|---|---|---|---|---|---|
| **Gradient boosting (XGBoost, LightGBM, CatBoost) / random forest** on tabular features (schedule, airport state, weather, previous-leg delay) | BTS, airline ops data, METAR | Hours to D-1 | Random forest network-state model: 19% classification error at the 60-min threshold, 2 h ahead; 21 min median error (TR-C 2014) [S-P40]. Many recent papers report >90% "accuracy" on imbalanced classes (e.g. SPIE 2024 XGBoost best [S-P53]), but these numbers are not meaningful without a base rate or horizon | Most widely used; strong baseline; the likely engine inside commercial tools [VALIDATE] | Leakage (using features that are not known at prediction time); class imbalance; a weak signal for rare causes (technical) |
| **ML take-off / ETA / TOBT prediction** | Flight plan, ETFMS, A-CDM milestones, historical | EOBT-1h to flight-plan filing | About 30% error reduction vs ETFMS [S-P36]; take-off uncertainty is the dominant ETA error source [S-P38] | Research → pilots at EUROCONTROL; vendors in production (FlightAware) [S-P35] | Needs an A-CDM/NM data feed; airline-side access varies |
| **Pre-tactical ATFM delay prediction** (four independent ML models) | NM historical regulations, traffic forecasts | D-1 | Not extracted (full text not read) [VALIDATE] | Academic [S-P39] | Regulations depend on ANSP staffing and strikes, which are hard to model |
| **Deep learning / spatio-temporal GNN** (airport graph, delay propagation) | Network-wide flights, weather | 1–3 h steps; e.g. SGDAN uses information available 3 h before departure [S-P44] | Outperforms purely temporal models on benchmark datasets [S-P43][S-P44] | Academic only (no airline production case found) | Data-hungry; hard to explain to controllers; benchmarks are not comparable |
| **Probabilistic / distributional models** (quantile regression, mixture density networks, Bayesian NN; survival model for propagation cited in a review) | Historical delays, METAR | Weeks to months (schedule planning) [S-P45]; D-1 (Schiphol thesis) [S-P46] | Better log-likelihood than baselines [S-P45] | Academic; fits planning buffers and risk-based decisions | Calibration must be monitored |
| **Predictive maintenance / prognostics** (Weibull reliability, anomaly detection, ML on sensor/fault data) | ACMS parameters, fault messages, removal history | Days to weeks | See §6 (Delta, easyJet, Emirates) | **Proven in production** (OEM platforms) | Vendor-reported benefits; data rights/OEM lock-in; false-alert workload [VALIDATE] |
| **Computer vision turnaround** | Ramp cameras | Minutes | Vendor claims (§6) | Production at some airports | Airport-owned cameras; labour-relations and privacy issues [VALIDATE] |
| **Optimisation (MIP, LNS, heuristics) for recovery** | Schedule, crew, aircraft, passenger data | Minutes to D-1 | SWISS OPSD results (§6) | **Proven in production** | Not prediction; consumes predictions |

**When rules or conventional analytics are enough** [PRACTICE/AI-OPP]:
- **Known external constraints.** A CTOT, EDCT, Ground Stop, published curfew or NOTAM closure is a *fact*, not a prediction. A deterministic propagation engine (rotation + minimum turn time + crew connection time) turns it into downstream delay. Delay propagation in OPSD is itself a **heuristic** [S-P31].
- **Rotation propagation in the next 1–3 legs.** Simple arithmetic is enough: inbound ETA + minimum turn time → new EOBT. ML adds value mainly in estimating the inbound ETA and the *actual* turn time, which can be shorter or longer than the minimum.
- **Threshold monitoring.** Statistical process monitoring and rules over OTP KPIs and A-CDM milestones (e.g. "TOBT not updated and boarding not started at STD-25") catch most turnaround slippage.
- **Where ML earns its place:**
  - (a) ETA/take-off time beyond the system estimates [S-P36];
  - (b) anticipating regulations, programs and weather impact *before* they are issued (D-1 to H-3) [S-P39];
  - (c) component failure prognostics [S-P25][S-P27];
  - (d) probabilistic risk scores used to rank which flights an OCC controller should look at first [AI-OPP].
- **Generative/LLM uses** (e.g. summarising NOTAMs and advisories) were outside the evidence base found in this pass [VALIDATE].

**Accuracy vs horizon (synthesis)** [ACADEMIC/VALIDATE]:
- Error grows as the horizon lengthens. Rebollo & Balakrishnan explicitly study 2–24 h horizons [S-P40], but the per-horizon figures were not extracted here.
- Close to departure (≤1–2 h), most of the delay is already visible: inbound position, CTOT/EDCT, TOBT. Models mostly refine an existing estimate.
- At D-1 and earlier, only distributions and risk rankings are realistic [S-P45][S-P46].
- Single-flight point predictions at D-1 should not be presented as deterministic.

## 8. Risks, limitations, airline-model differences

**Data-quality pitfalls**
- **Label noise in delay codes.** [PRACTICE]
  - Codes are allocated by staff under time pressure.
  - Codes 00–05 are airline-internal [S-P04].
  - Weather appears in several places: 71–77; 84; 89 only under an ATFM regulation [S-P04]; and in BTS "NAS" and "Late Aircraft" as well as "Extreme Weather" [S-P07].
  - Old BTS help text notes that carriers do not report the root cause of late-arriving aircraft [S-P07].
- **Conflicts to flag.**
  - CODA reports "reactionary: codes 90–96" [S-P01], while AHM 730 as summarised by ANS Performance lists 91–96 [S-P04]. Treat 90 as non-standard or legacy [VALIDATE].
  - CODA counts delay from 1 min [S-P01]; BTS uses 15 min [S-P07]. European and US datasets are not directly comparable.
  - AHM 730/731 vs AHM 732: the industry is mid-transition, so historical training data may mix schemas [S-P05][S-P06][VALIDATE].
  - TAF validity rules differ across Annex 3 versions [S-P22][S-P23].
  - Google's "≥80% confident" was reported as "80% accurate" in the press [S-P34].
- **Coverage gaps.**
  - CODA monthly data can be partial (57.1% coverage, Sep 2026) and is revised later [S-P01].
  - ASPM excludes cancellations and is login-restricted [S-P18].
  - ADRR is R&D-only and cannot be redistributed [S-P19].
  - OpenSky has oceanic/remote gaps [S-P20][S-P21].
- **Outdated sources.** The 2014 random-forest results use 2007–2008 data [S-P40], the Google/United cases are from 2018/2019, and the Delta 2010→2018 numbers predate COVID-era fleet and crew changes. They are still useful as patterns, but current figures need confirming [VALIDATE].
- **Leakage and evaluation.** [ACADEMIC] Many papers report accuracy on random splits, with features unavailable at prediction time and imbalanced classes. A practitioner account stresses that live operational signals beat batch-trained models, and that controllers need explanations [S-P56] (Tier 4). Carvalho et al. call for clearer taxonomies of horizon, scope and data [S-P41].
- **Rare events.** Cancellations are rare relative to delays. Imbalance handling changes F1 dramatically in thesis work [S-P54]. Storm-day cascades (Southwest 2022) are partly driven by recovery-system capacity, which a delay model does not capture [S-P49].
- **Automation bias and workload.** False alerts from maintenance prognostics or risk scores consume controller and engineer time. Thresholds should be tuned with the OCC [VALIDATE].
- **Vendor and OEM claims** dominate the production evidence (Airbus, Boeing, FlightAware, Assaia). Treat them as upper bounds until confirmed with an airline.

**Airline-model differences** (largely [VALIDATE] — not directly evidenced by segment-level data in this pass):
- **LCC / point-to-point** (e.g. easyJet, Ryanair):
  - High utilisation, short turns and many sectors per tail per day mean reactionary delay builds through the day. First-wave protection is critical [S-P03].
  - Few connections, so passenger-connection prediction matters less; the rotation is the main exposure.
  - EUROCONTROL reports low-cost at 10,788 daily flights in 2025 with 76.1% arrival OTP15 for that segment (network-level comparison not extracted) [S-P52].
  - Base/night-stop structure makes spare-aircraft positioning a D-1 decision.
- **Hub / full-service** (e.g. Delta, United, SWISS):
  - Banked waves mean a hub weather or ATC event (GDP, ATFM regulation) hits many connections at once.
  - Connection-hold decisions [S-P33] and integrated recovery [S-P31] add value.
  - Wide-body technical delays are costly: long-haul, slot-constrained, EU261 at 3 h+.
- **Regional / capacity-purchase carriers**:
  - Smaller turboprop/regional jet fleets with limited spares and crew bases.
  - Strongly exposed to weather and de-icing, and to hub GDPs imposed on the mainline partner.
  - The data may sit partly in the mainline partner's systems [VALIDATE].
- **Regional differences:**
  - Europe is dominated by ATFM capacity, staffing and weather (summer 2025 en-route ATFM delay 3.1 min/flight, down 32% from 4.6) [S-P15].
  - The US is dominated by GDP/GS programs at major hubs and convective weather [S-P10].

## 9. Open questions / knowledge gaps / items to validate with an airline

1. Which delay-code scheme does the airline use today (AHM 730/731 or AHM 732)? How reliable is code allocation, and is there a post-flight audit? [VALIDATE]
2. Which OCC, crew and maintenance systems are in place (vendor/version)? Do they already offer delay or ETA predictions? Which real-time feeds are available: NM B2B, A-CDM DPI, FAA SWIM, ACARS, OEM health platform? [VALIDATE]
3. Exact decision deadlines per process, e.g. the latest time to pre-cancel, swap tails, call reserve crew, or hold for connections. Who has authority at each point? [VALIDATE]
4. What lead time and precision would change a decision (e.g. "≥70% probability of >60 min delay at H-3")? The cost of a false alarm vs a miss. [VALIDATE]
5. EUROCONTROL CTOT allocation timing and the SAM/SRM/SLC message semantics. The ATFCM Operations Manual (2025/2026 editions) was not read. [VALIDATE]
6. CODA Digest Annual 2025 figures (not found). The 2024 digest is still marked "Working Draft" in the version seen. [VALIDATE]
7. Per-horizon accuracy figures from Rebollo & Balakrishnan 2014 and the results of Mas-Pujol & Delgado 2024 were not extracted (full texts not read). [VALIDATE]
8. Whether the Delta OCC ML platform (2020), Google Flights delay predictions and United ConnectionSaver are still in use, and in what form. [VALIDATE]
9. Whether EUROCONTROL Innovation Hub TOBT models are operational at Prague and Fiumicino. [VALIDATE]
10. Current ICAO Annex 3 text for TAF/METAR/SIGMET issuance and IWXXM status. [VALIDATE]
11. Crew legality rules (EASA ORO.FTL / FAA Part 117 / national) and how crew-disruption risk is detected today. Deferred to the §15.7.2 note. [VALIDATE]
12. Segment-level reactionary-delay data (LCC vs hub vs regional) is still a gap. EUROCONTROL market-segment tables could fill it. [VALIDATE]
13. Status of the 2026 DOT proposal on the Air Carrier delay category. [VALIDATE]

## 10. Sources

Tier: 1 = authoritative (IATA/ICAO/FAA/EASA/EUROCONTROL/government/airline official); 2 = industry/vendor; 3 = academic; 4 = community/practitioner. "Search summary only" means the page content was seen through search-result extraction, not a full fetch.

| ID | Tier | Title | Publisher/author | Publication date | URL | Accessed | What it supports |
|---|---|---|---|---|---|---|---|
| S-P01 | 1 | CODA monthly punctuality/delay report — September 2026 | EUROCONTROL CODA | 23 Oct 2026 | https://www.eurocontrol.int/archive_download/all/node/16240 | 2026-11-20 | Avg delay 15.0 min dep; reactionary 7.1 min; CODA code groupings (reactionary 90–96); 57.1% coverage; delay from 1 min |
| S-P02 | 1 | CODA Digest Annual 2024 (status line "Working Draft") | EUROCONTROL CODA | 2025 (exact date not seen) | https://www.eurocontrol.int/archive_download/all/node/15406 | 2026-11-20 | Reactionary 46% of delay minutes, 8.0 min/flight; 69.2% dep OTP15 (search summary only) |
| S-P03 | 1 | EUROCONTROL Data Snapshot #59 — better "first wave" performance | EUROCONTROL | 12 May 2026 | https://www.eurocontrol.int/publication/eurocontrol-data-snapshot-59-better-first-wave-performance | 2026-11-20 | First-wave and all-day delay reduction; punctuality vs connections trade-off |
| S-P04 | 1 | IATA delay codes (definition page) | EUROCONTROL PRU / ANS Performance | n.d. | https://www.ansperformance.eu/definition/iata-delay-codes/ | 2026-11-20 | AHM 730 code groups and meanings 81–99; AHM 780 |
| S-P05 | 1 | On-demand webinar: New IATA delay codes AHM 732 | IATA Knowledge Hub | 3 Mar 2023 | https://www.iata.org/en/publications/newsletters/iata-knowledge-hub/on-demand-webinarnew-iata-delay-codes-ahm-732-how-to-improve-performance-analysis/ | 2026-11-20 | Existence and purpose of AHM 732 |
| S-P06 | 1 | AIDX XML Implementation Guide v22.1 | IATA | n.d. (v22.1) | https://www.iata.org/contentassets/cfe998bcf9214859afda9c8bf4ff75c3/aidx-xml-imp-guide-v22.1.pdf | 2026-11-20 | ReasonCode → AHM 732; AHM 47th ed. process matrix (search summary only) |
| S-P07 | 1 | Airline On-Time Performance and Causes of Flight Delays | US DOT / BTS | n.d. | https://www.bts.gov/topics/airlines-and-airports/airline-time-performance-and-causes-flight-delays | 2026-11-20 | Five cause categories; 15-min threshold; late-aircraft caveat (fetch returned 403; search summary only) |
| S-P08 | 1 | 14 CFR Part 234 — Airline Service Quality Performance Reports | US eCFR | current | https://www.ecfr.gov/current/title-14/chapter-II/subchapter-A/part-234 | 2026-11-20 | On-time definitions and reporting obligation (search summary only) |
| S-P09 | 1 | DOT notice 2026-18040 (Federal Register public inspection) | US DOT | 2026 | https://public-inspection.federalregister.gov/2026-18040.pdf | 2026-11-20 | Proposed revision of "Air Carrier" delay category (status unverified) |
| S-P10 | 1 | FAA JO 7210.3 Ch. 18 Traffic Management; FAA OIS help (GDP) | FAA | current | https://www.faa.gov/air_traffic/publications/atpubs/foa_html/chap18_section_10.html ; https://www.fly.faa.gov/ois/help/index.html | 2026-11-20 | GDP, GS, EDCT, ATCSCC, ground-stop limits (search summary only) |
| S-P11 | 1 | AIP ENR 1.9 Air Traffic Flow Management | FAA | current | https://www.faa.gov/Air_Traffic/publications/atpubs/aip_html/part2_enr_section_1.9.html | 2026-11-20 | US ATFM programs (search summary only) |
| S-P12 | 2 | Ground Delay Program (GDP) | NBAA | n.d. | https://nbaa.org/aircraft-operations/airspace/tfm/tools-used-for-traffic-flow-management/ground-delay-program-gdp/ | 2026-11-20 | GS replaced by GDP when the duration is unclear |
| S-P13 | 2 | Calculated Take Off Time (CTOT) | SKYbrary | n.d. | https://skybrary.aero/articles/calculated-take-time-ctot | 2026-11-20 | CTOT definition, issuer, −5/+10 tolerance |
| S-P14 | 1 | Commission Regulation (EU) No 255/2010 (ATFM common rules) | EU / EUR-Lex | 2010 | https://eur-lex.europa.eu/eli/reg/2010/255/oj/eng | 2026-11-20 | ATFM slot definition, adherence monitoring (search summary only) |
| S-P15 | 1 | Special Flash Briefing — Summer 2025 | EUROCONTROL | Sep 2025 | https://www.eurocontrol.int/sites/default/files/2025-09/eurocontrol-special-flash-briefing-summer-2025.pdf | 2026-11-20 | En-route ATFM delay 3.1 vs 4.6 min/flt; capacity/staffing/weather shares (search summary only) |
| S-P16 | 1 | Connecting airports with the ATM network (A-CDM/DPI) | ICAO MID A-CDM workshop (EUROCONTROL presentation) | 2023 | https://www.icao.int/MID/Documents/2023/ACDM/PPT_9%20-%20Connecting%20airports%20with%20the%20ATM%20network.pdf | 2026-11-20 | DPI types and timing; ≥5-min update rule (search summary only) |
| S-P17 | 2 | A Ground Handler's Guide to A-CDM (EIDW) | Dublin Airport (daa) | n.d. | https://www.dublinairport.com/docs/default-source/default-document-library/a-ground-handlers-guide-to-a-cdm_eidw.pdf | 2026-11-20 | TOBT >15 min beyond EOBT → DLA (search summary only) |
| S-P18 | 1 | Aviation System Performance Metrics (ASPM) help | FAA | current | https://aspmhelp.faa.gov/index/Aviation_Performance_Metrics_(APM).html | 2026-11-20 | ASPM scope, login, inputs, no cancellations (with NAP 2018 and Wikipedia cross-check, search summary only) |
| S-P19 | 1 | Aviation Data for Research (ADRR) | EUROCONTROL | updated 2026 | https://www.eurocontrol.int/dashboard/aviation-data-research | 2026-11-20 | Research data access, terms, volume |
| S-P20 | 3 | Trino — Historical Data | OpenSky Network | current | https://openskynetwork.github.io/opensky-api/trino.html | 2026-11-20 | Historical ADS-B access via Trino |
| S-P21 | 3 | Crowdsourced air traffic data from the OpenSky Network (ESSD 13, 357) and OpenSky Report 2025 (ADS-C) | Copernicus ESSD; arXiv 2505.06254 | 2021; 2025 | https://essd.copernicus.org/articles/13/357/2021/ ; https://arxiv.org/html/2505.06254v1 | 2026-11-20 | Coverage limits; ADS-C addition |
| S-P22 | 1 | ICAO Annex 3, 16th ed., Amendment 74 (WMO-hosted copy) | ICAO / WMO | 2008 | https://old.wmo.int/extranet/pages/prog/www/ISS/Meetings/CT-MTDCF-ET-DRC_Geneva2008/Annex3_16ed_AMD74.pdf | 2026-11-20 | TAF validity 6–30 h; issuance intervals (outdated edition; search summary only) |
| S-P23 | 2 | Terminal Aerodrome Forecast (TAF) | SKYbrary | n.d. | https://skybrary.aero/articles/terminal-aerodrome-forecast-taf | 2026-11-20 | Common 30-h TAF practice (search summary only) |
| S-P24 | 1 | FAA Holdover Time Guidelines Winter 2026–2027 | FAA | 11 Aug 2026 | https://www.faa.gov/other_visit/aviation_industry/airline_operators/airline_safety/deicing/FAA-2026-27_Holdover_Tables.pdf | 2026-11-20 | HOT guidelines, DSHOT, 121.629(c) (search summary only) |
| S-P25 | 2 | Keeping the fleet flying (Skywise Fleet Performance+) | Airbus | 22 Oct 2024 | https://www.aircraft.airbus.com/en/newsroom/news/2024-10-keeping-the-fleet-flying | 2026-11-20 | easyJet avoided cancellations; 11,600 aircraft; 180+ items; Digital Alliance |
| S-P26 | 2 | Skywise Health Monitoring | Airbus | n.d. | https://aircraft.airbus.com/en/services/enhance/skywise/skywise-solutions/skywise-health-monitoring | 2026-11-20 | Emirates ~1% reliability, Cebu Pacific quote (search summary only) |
| S-P27 | 1 | Delta TechOps expanding predictive maintenance capabilities with new Airbus partnership | Delta TechOps | 16 Oct 2019 | https://deltatechops.com/delta-techops-expanding-predictive-maintenance-capabilities-with-new-airbus-partnership/ | 2026-11-20 | 5,600→55 maintenance cancellations; >95% prediction success; PRM/Skywise |
| S-P28 | 2 | Airplane Health Management (AHM) | Boeing Global Services | n.d. | https://services.boeing.com/maintenance-engineering/maintenance-optimization/airplane-health-management-ahm | 2026-11-20 | AHM scope, scale claims, Insight Accelerator (search summary only) |
| S-P29 | 2 | Delta Air Lines bets on AI to help its operations run smoothly in bad weather | TechCrunch | 7 Jan 2020 | https://techcrunch.com/2020/01/07/delta-air-lines-bets-on-ai-to-help-its-operations-run-smoothly-in-bad-weather/ | 2026-11-20 | Delta OCC ML platform (search summary only) |
| S-P30 | 1 | Booth speaker series CES 2020: how AI is helping Delta predict the unpredictable | Delta News Hub | Jan 2020 | https://news.delta.com/booth-speaker-series-ces-2020-how-ai-helping-delta-predict-unpredictable | 2026-11-20 | "Millions of data points"; spring 2020 live launch (search summary only) |
| S-P31 | 3 | Decision Support for Schedule Recovery at Lufthansa Group Airlines | Davies et al., INFORMS J. Applied Analytics 56(1):58–75, doi 10.1287/inte.2025.0296 | 2026 | https://www.business.uzh.ch/dam/jcr:d5051dd1-ce0f-4104-9f4b-5c9603ea6c65/davies-et-al-2026-decision-support-for-schedule-recovery-at-lufthansa-group-airlines.pdf | 2026-11-20 | OPSD design, adoption metrics, decision-timing quote |
| S-P32 | 1 | Lufthansa Group and Google Cloud: more stability and reliability for customers | Lufthansa Group | 20 Jan 2020 | https://newsroom.lufthansagroup.com/en/more-stability-and-reliability-for-lufthansa-group-customers/ | 2026-11-20 | OPSD origin; SWISS test launch |
| S-P33 | 1 | United Airlines makes connecting the world easier than ever with ConnectionSaver | United Airlines | 10 Jun 2019 | https://united.mediaroom.com/2019-06-10-United-Airlines-Makes-Connecting-the-World-Easier-Than-Ever-with-ConnectionSaver | 2026-11-20 | Connection-hold decision support and outcomes (search summary + Cranky Flier cross-check) |
| S-P34 | 2 | Google Flights will now predict airline delays — before the airlines do | TechCrunch (Google announcement) | 31 Jan 2018 | https://techcrunch.com/2018/01/31/google-flights-will-now-predict-airline-delays-before-the-airlines-do/ | 2026-11-20 | 80% confidence threshold; press misreporting (search summary only) |
| S-P35 | 2 | FlightAware Foresight | FlightAware | current | https://www.flightaware.com/commercial/foresight/ | 2026-11-20 | ML ETA claims (30–50%) (search summary only) |
| S-P36 | 3 | An explainable machine learning approach to improve take-off time predictions | Dalmau, Ballerini, Naessens, Belkoura, Wangnick; J. Air Transport Management 95, doi 10.1016/j.jairtraman.2021.102090 | 2021 | https://ideas.repec.org/a/eee/jaitra/v95y2021ics0969699721000739.html | 2026-11-20 | ~30% error reduction vs ETFMS at EOBT-1h |
| S-P37 | 3 | SESAR Innovation Days 2023, paper 26 (probabilistic turnaround/TOBT) | EUROCONTROL Innovation Hub authors | 2023 | https://www.sesarju.eu/sites/default/files/documents/sid/2023/Papers/SIDs_2023_paper_26%20final.pdf | 2026-11-20 | TOBT ML; stated deployment plans (search summary only) |
| S-P38 | 3 | SESAR Innovation Days 2023, paper 53 (ETA predictability) | EUROCONTROL Innovation Hub authors | 2023 | https://www.sesarju.eu/sites/default/files/documents/sid/2023/Papers/SIDs_2023_paper_53%20final.pdf | 2026-11-20 | Take-off uncertainty dominates ETA error (search summary only) |
| S-P39 | 3 | Pre-tactical prediction of ATFM delay for individual flights (ESWA 252A, 124146; DASC 2022 version) | Mas-Pujol & Delgado | 2024 | https://westminsterresearch.westminster.ac.uk/item/vzq04/pre-tactical-prediction-of-atfm-delay-for-individual-flights | 2026-11-20 | D-1 ATFM delay prediction concept (full text not read) |
| S-P40 | 3 | Characterization and prediction of air traffic delays (TR-C, doi 10.1016/j.trc.2014.04.007; 2012 MIT thesis) | Rebollo & Balakrishnan | 2014 (thesis 2012) | https://dspace.mit.edu/handle/1721.1/111158 | 2026-11-20 | RF network-state model; 2 h: 19% classification error / 21 min median error; 2–24 h horizons |
| S-P41 | 3 | On the relevance of data science for flight delay research: a systematic review | Carvalho et al., Transport Reviews 41(4):499–528 | 2021 | https://ideas.repec.org/a/taf/transr/v41y2021i4p499-528.html | 2026-11-20 | Taxonomy; methodological issues |
| S-P42 | 3 | A Review on Flight Delay Prediction (arXiv 1703.06118) | Sternberg, Soares, Carvalho, Ogasawara | 2017 (v3 2021) | https://arxiv.org/abs/1703.06118v3 | 2026-11-20 | Review of methods; survival/density model references |
| S-P43 | 3 | Spatiotemporal Propagation Learning for Network-Wide Flight Delay Prediction (arXiv 2207.06959) | Wu et al. | 2022 | https://arxiv.org/pdf/2207.06959 | 2026-11-20 | GNN propagation model |
| S-P44 | 3 | SGDAN — spatio-temporal graph dual-attention network for quantified flight delay prediction | Guo et al., Sensors | 2020 | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7696102/ | 2026-11-20 | GNN; 3 h pre-departure information |
| S-P45 | 3 | Modeling Probability Distributions of Primary Delays in the National Air Transportation System (TRR 2569) | Wang & Vaze | 2016 | https://mdsg.engineering.dartmouth.edu/Wang_Vaze_modeling_probability_distributions_of_delays.pdf | 2026-11-20 | Weeks-to-months distributions for schedule planning |
| S-P46 | 3 | Predicting Probabilistic Flight Delay for Individual Flights using Machine Learning Models (MSc thesis) | Vorage, TU Delft | 2021 | https://repository.tudelft.nl/record/uuid:e06d4f4c-8f9e-49a3-a841-463efc6d35af | 2026-11-20 | D-1 per-flight delay distributions at Schiphol (search summary only) |
| S-P47 | 2 | Assaia ApronAI / POBT glossary / JFKIAT case | Assaia | various | https://www.assaia.com/solutions/apron-ai | 2026-11-20 | Computer-vision POBT; vendor results (search summary only) |
| S-P48 | 1 | ML airport surface model (DASC 2023) | NASA | 2023 | https://ntrs.nasa.gov/api/citations/20230011430/downloads/20230011430_DASC_ml_airport_surface_model_final.pdf | 2026-11-20 | ML runway/taxi predictions at DFW; field evaluation (search summary only) |
| S-P49 | 1 | DOT penalizes Southwest Airlines $140 million for 2022 holiday meltdown | US DOT | Dec 2023 | https://www.transportation.gov/briefing-room/dot-penalizes-southwest-airlines-140-million-2022-holiday-meltdown | 2026-11-20 | 16,900 cancellations; penalty; crew-system role (press) |
| S-P50 | 1 | Southwest Airlines — Order 2025-12-4 (amended consent order) | US DOT | Dec 2025 | https://www.transportation.gov/sites/dot.gov/files/2025-12/Southwest%20Airlines%20-%20Order%202025-12-4.pdf | 2026-11-20 | Modernised crew ops, movement control, recovery optimisers (search summary only) |
| S-P51 | 1 | CJEU Sturgeon (C-402/07, C-432/07) and related press releases | Court of Justice of the EU | 2009; 2012 | https://curia.europa.eu/jcms/jcms/p1_2018879/en | 2026-11-20 | 3-h compensation; extraordinary circumstances; duty of care (search summary only) |
| S-P52 | 1 | EUROCONTROL Data Snapshot #57 | EUROCONTROL | Jan 2026 | https://www.eurocontrol.int/sites/default/files/2026-01/eurocontrol-data-snapshot-57.pdf | 2026-11-20 | Low-cost segment volume and punctuality 2025 (search summary only) |
| S-P53 | 3 | Flight delay prediction based on machine learning method (Proc. SPIE 13281) | SPIE conference authors | 27 Sep 2024 | https://electronicimaging.spiedigitallibrary.org/conference-proceedings-of-spie/13281/132810R/Flight-delay-prediction-based-on-machine-learning-method/10.1117/12.3050964.full | 2026-11-20 | Boosting comparison (weak evidence) |
| S-P54 | 3 | TU Delft MSc thesis on delay/cancellation classification with imbalance handling | TU Delft repository | n.d. | https://repository.tudelft.nl/file/File_4fd9215b-60ef-44b9-bcc2-6d7531f493c2 | 2026-11-20 | Cancellation imbalance; horizons 5/1/0 days (search summary only) |
| S-P55 | 3 | Lufthansa × Celonis rotational delay prediction (TUM Data Innovation Lab report) | TUM MDSI | 2021 | https://www.mdsi.tum.de/fileadmin/w00cet/di-lab/pdf/Lufthansa_Celonis_WS2021_FinalReport.pdf | 2026-11-20 | Student prototype, not production evidence |
| S-P56 | 4 | Flight delay prediction with machine learning: lessons from production | DEV Community (practitioner blog) | n.d. | https://dev.to/airtruffle/flight-delay-prediction-with-machine-learning-lessons-from-production-4njm | 2026-11-20 | Staleness, live signals, explainability (single practitioner account) |
