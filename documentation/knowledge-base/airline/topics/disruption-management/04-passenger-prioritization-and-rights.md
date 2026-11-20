# 04 – Intelligent Passenger Prioritisation and Passenger-Rights Constraints (§15.7.4)

> Research question: *How can AI help an airline prioritise passenger recovery intelligently when alternative inventory is limited?*
> Scope: how airlines order passengers for reaccommodation and denied boarding, and the legal passenger-rights regimes that bound any such ordering.
> Status: first pass, researched 2026-11-20.
> Labels: `[STD]` regulation/standard · `[PRACTICE]` common practice · `[SPECIFIC]` one airline or vendor · `[ACADEMIC]` research · `[AI-OPP]` potential AI improvement · `[VALIDATE]` to confirm.
> Related notes (same folder): [00-OVERVIEW](00-OVERVIEW.md) · [01 prediction](01-disruption-prediction.md) · [02 network impact & recovery](02-network-impact-and-recovery.md) · [03 passenger impact](03-passenger-impact.md) · [04 prioritisation & rights](04-passenger-prioritization-and-rights.md) · [05 OCC/PCU & systems](05-occ-pcu-workflows-and-systems.md). Sources: [`../../SOURCES.md`](../../SOURCES.md) (IDs are namespaced per note and final; no renumbering). Glossary: [`../../GLOSSARY.md`](../../GLOSSARY.md).

---

## 1. Key findings

1. **[STD] The law sets the first tier of any priority order, not commercial value.** EU261/UK261 Art. 11(1) requires carriers to "give priority to carrying persons with reduced mobility … as well as unaccompanied children" [S-R03]. Canada's APPR s. 15(4) fixes the order for involuntary denied boarding: unaccompanied minor, then a person with a disability with their support person or animal, then families, then passengers already denied boarding on the same ticket [S-R24]. Brazil's ANAC Res. 400 Art. 28 gives PNAE (passengers needing special assistance) priority in reaccommodation. It also says reaccommodation takes precedence over new sales [S-R31]. The US 14 CFR 250.3(b) instead *permits* carriers to rank by check-in time, seat assignment, fare paid, frequent-flyer status, disability or unaccompanied-minor status. Rules must be understandable and must not cause "unjust prejudice" [S-R11].
2. **[SPECIFIC] Commercial ranking is real and published in the US.** Delta's International Conditions of Carriage Rule 21(C) (updated 18 Aug 2026) protects confirmed First/Business passengers, Diamond/Platinum/Gold Medallion members and corporate-contract passengers before Coach passengers. It then ranks by boarding pass, IROPS-rebooked status, lower elite tiers, class of service and check-in time. Passengers with disabilities and unaccompanied minors may be accommodated "without regard to" that order [S-R40]. Alaska ranks only by seat assignment and check-in time, with hardship exceptions [S-R41]. Practice varies by airline, so no single ordering is universal.
3. **[STD] EU261 has been revised. Regulation (EU) 2026/2202 was published in the OJ on 2 Oct 2026, entered into force 22 Oct 2026, and most provisions apply from 23 Oct 2027** [S-R05][S-R06]. Compensation stays at €250/€400/€600 with a 3-hour arrival-delay trigger, measured on the whole journey [S-R04]. New hard constraints relevant to prioritisation:
   - Rerouting must consider other carriers and other modes.
   - If no comparable rerouting is offered within 3 h, the passenger may self-reroute and recover up to 400 % of the ticket price.
   - A wider "specific needs" group (PRM, infants, unaccompanied minors, pregnant women, medical cases) keeps accommodation rights even in extraordinary circumstances.
   - A missed-connection article 6b [S-R04][S-R06].
   The joint text is the pre-legal-linguistic version, so check the final OJ wording **[VALIDATE]**.
4. **[STD] The US position changed in 2025.** DOT abandoned (Sept 2025) and formally withdrew (Nov 2025) the proposed cash compensation for controllable delays and cancellations [S-R17][S-R18]. Automatic refunds (14 CFR 260, April 2024 rule; significant change = 3 h domestic / 6 h international) remain. DOT granted enforcement discretion for renumbered flights, extended to 7 Jul 2027 [S-R13][S-R15]. US protection therefore rests on refunds, denied-boarding compensation (DBC), tarmac rules and voluntary customer-service commitments [S-R19].
5. **[AI-OPP] The defensible architecture is lexicographic, not a single blended score.** It has four layers:
   - Hard legal and safety constraints, which are feasibility, not weights.
   - Legally mandated priority groups.
   - Operational urgency: last-flight-of-day, connection protection, time-to-deadline.
   - A configurable commercial or wellbeing score, used only as a tie-breaker within a tier.
   Vendors already offer value-based rebooking (Amadeus, Sabre) [S-R43][S-R46]. Published evidence of *fairness-constrained* or explainable passenger ranking is thin.
6. **[STD]/[VALIDATE] Privacy and fairness risk is material.** Disability, medical and pregnancy SSRs are GDPR special-category data. Ranking that "solely" automatically decides who is stranded may engage GDPR Art. 22: the CJEU *SCHUFA* judgment (C-634/21, 7 Dec 2023) held that a score can itself be the decision when it plays a determining role [S-R38][S-R39]. Human-in-the-loop review and published criteria are the safe default.

---

## 2. Domain fundamentals & terminology

| Term | Meaning | Source |
|---|---|---|
| Reaccommodation / rebooking / reprotection | Moving a disrupted passenger to an alternative flight (own, partner, interline or other mode). | [S-R44][S-R48] |
| Rerouting (EU261 Art. 8) | Passenger's choice of onward carriage "under comparable transport conditions" at earliest opportunity or later date at their convenience, vs reimbursement. | [S-R01][S-R04] |
| Denied boarding (DB) / IDB / VDB | Refusal to carry a passenger holding a confirmed reservation who presented on time. Involuntary (IDB) follows a call for volunteers (VDB). The revised EU261 extends the concept beyond overbooking to operational reasons. | [S-R11][S-R06] |
| Boarding priority rules | The carrier's written criteria for choosing who is involuntarily denied boarding. Mandatory in the US (14 CFR 250.3). | [S-R11] |
| PRM | Person with reduced mobility. In the EU, defined by Reg. 1107/2006, with assistance pre-notified at least 48 h before departure. | [S-R36] |
| PNAE | *Passageiro com Necessidade de Assistência Especial* (Brazil; ANAC Res. 280/2013). Has reaccommodation priority under Res. 400 Art. 28. | [S-R31] |
| UMNR | Unaccompanied minor. EU joint text defines "unaccompanied minor" as under 18. Airline acceptance ages vary. | [S-R04][S-R41] |
| Extraordinary circumstances | EU/UK defence against compensation (not against care): events not inherent in normal activity and beyond actual control. Wallentin-Hermann test, codified with a non-exhaustive Annex in 2026/2202. | [S-R04][S-R06] |
| Controllable / within carrier control | US dashboard and Canadian APPR concept that decides which commitments or compensation apply. | [S-R19][S-R24] |
| Significant change (US) | Departure or arrival moved ≥3 h domestic or ≥6 h international, among other triggers. Gives an automatic refund right. | [S-R13][S-R14] |
| Tarmac delay | On-board delay on the ground. US limits: 3 h domestic, 4 h international (14 CFR 259.4). EU revision adds 2 h disembarkation at EU airports. | [S-R16][S-R04] |
| Final destination | Destination on the last ticketed segment. EU compensation is measured on arrival delay there (*Folkerts*, C-11/11). | [S-R09] |
| IATA Res. 735d | IATA standard for involuntary rerouting and reissue. Binding on IATA members and MITA participants. Only IATA members can be offered under it. | [S-R48] |
| Fare value / booking class / cabin | Revenue paid and RBD. Used by some carriers as a DB or rebooking tiebreaker (permitted in the US). | [S-R11][S-R40] |
| CLV | Customer lifetime value: predicted future margin of a customer. Vendor inputs include "passenger value" and "loyalty score". | [S-R45] |
| SDR / DES | Special Drawing Right (IMF unit), used by Montreal Convention and ANAC (DES). | [S-R22][S-R31] |

---

## 3. Processes, decisions & timing

**3.1 Typical sequence when inventory is short** [PRACTICE] [S-R44][S-R48]
1. **Detect** the disruption: cancellation, long delay, missed connections forecast, or oversale/downgauge.
2. **Determine the regime(s).** Which apply depends on departure airport, carrier licence and route; one PNR can sit under several (e.g. EU-departing on a US carrier = EU261 + DOT refund rules) **[VALIDATE per itinerary]**.
3. **Protect mandatory groups first:** PRM/PNAE, UMNR, families with young children (seating rules in Canada and the EU revision), passengers with medical clearance, and passengers who were already denied boarding [S-R24][S-R04].
4. **Build the alternatives pool** in this order:
   - Own metal.
   - Partner/JV.
   - Interline (IATA 735d/bilateral).
   - Other carriers.
   - Ground transport.
   Legal timing gates trigger escalation along this list:
   - Canada (large carrier): 9 h own/partner, then any carrier within 48 h.
   - EU revision: 3 h to offer comparable rerouting, or the passenger may self-reroute.
   [S-R24][S-R04]
5. **Allocate seats** (rules engine or optimiser). Ordering is applied when demand > supply.
6. **Offer and notify** (auto-rebook plus self-service alternatives; refund option where legally required). Air Canada example: ~90 % of disrupted passengers get an automatic proposal, on average about 10 minutes after the cancellation notice. The KPI is an offer within 30 minutes [S-R44].
7. **Care and compensation.** Meals, hotel and communications by time thresholds (table §5). Compensation: EU revision requires information on compensation rights within 96 h and claim decisions within 30 days [S-R04][S-R06].
8. **Manual queue** for complex cases (~10 % at Air Canada) [S-R44].

**3.2 Decision owners** [PRACTICE] [VALIDATE]
- OCC decides which flights to cancel or delay.
- The Passenger Control Unit / Customer Recovery (Air Canada's "customer recovery team") run the reaccommodation policy.
- Revenue Management sets how much future inventory may be consumed. Amadeus describes "balanc[ing] seat sales against re-accommodation obligations" [S-R43].
- Airport/station staff execute denied boarding at the gate.
- Legal/Customer Relations own compensation.
Approval levels and who may override priority rules differ by airline and must be validated.

**3.3 Time-sensitivity drivers** [PRACTICE]/[STD]
- Last flight of the day: an overnight stay triggers hotel duties in every regime.
- Connections with long gaps to the next frequency.
- Legal clocks: EU 3 h rerouting offer; EU 5 h reimbursement offer (Art. 6(3) and 6b(2) in the revision); Canada 9 h/48 h; US 3 h/6 h refund trigger; ANAC 4 h alternatives.
- Visa/transit restrictions on alternative routings **[VALIDATE]**.

---

## 4. Data requirements (incl. privacy-sensitive data)

| Data | Typical origin | Use in prioritisation | Sensitivity |
|---|---|---|---|
| PNR segments, final destination, married segments, ticket coupon status | PSS reservations/ticketing | Connection exposure, number of affected segments, destination-based compensation distance (EU revision measures the whole journey) | Personal data |
| Check-in time, seat assignment, boarding pass status | DCS | US-style DB priority factors (Delta, Alaska) [S-R40][S-R41] | Personal |
| SSRs: WCHR/WCHS/WCHC, BLND, DEAF, MEDA, UMNR, pregnancy, infant (INF) | PSS/DCS, PRM pre-notification (1107/2006 Art. 6) | Mandatory priority and care tiers | **Special-category (health) data, GDPR Art. 9** [S-R38]. Minimise and restrict access |
| Family/group links (multi-PNR groups, children <14) | PNR | Keep together; Canada and the EU revision have seating duties [S-R24][S-R04] | Personal (children) |
| Fare paid, RBD, cabin, fare family, ticket restrictions | Ticketing/revenue accounting | Tiebreakers; downgrade refund obligations; DBC calculation (US DBC is % of one-way fare) [S-R11] | Commercial / personal |
| FFP tier, corporate contract code, OSI | Loyalty, CRM, corporate deals | Commercial tiers (Delta Rule 21) [S-R40] | Personal; profiling |
| Ancillaries purchased (EMDs) | PSS/EMD | Refund of unused ancillaries on DB (14 CFR 250.5(f)) [S-R11]; possible value input | Personal |
| CLV / "passenger value" / "loyalty score" | CRM/analytics | Vendor optimiser inputs [S-R45] | **Profiling (GDPR Art. 4(4), Art. 22)** |
| Past disruptions suffered | CRM, disruption history | SabreSonic historically scored "past service disruptions" [S-R47]; fairness/recency rule | Profiling |
| Inventory: own, partner, interline availability; IATA 735d eligibility; ground options | Inventory/availability, partner APIs | Feasible-alternatives pool | Commercial |
| Regime applicability: departure/arrival country, operating carrier licence | Schedule + reference data | Constraint selection | Non-personal |
| Disruption cause code (controllable / extraordinary / safety) | OCC/MRO | Compensation liability; drives EU/Canada burden of proof | Must be evidenced; audit trail |

Data-quality caveats [VALIDATE]:
- PRM needs are often not pre-notified (1107/2006 requires "reasonable efforts" anyway [S-R36]). The EU revision accepts notification as late as the disruption notice [S-R04].
- Pregnancy and medical needs are rarely in the PNR.
- CLV models are proprietary and can be stale.

---

## 5. Business rules & constraints

**5.1 Precedence of rule types** (the user's principle, consistent with every regime reviewed)
1. **Safety and security** (crew/aircraft limits, weight & balance, PRM numbers per flight, refusal on safety grounds) [STD].
2. **Legal passenger rights**: care, rerouting, refund and compensation duties, mandated priority groups, non-discrimination (ACAA 14 CFR 382; EC 1107/2006) [STD].
3. **Contractual obligations**:
   - Conditions of carriage/tariffs, e.g. Delta Rule 20 (rebooking on other carriers at Delta's discretion) and Alaska Rule 8 [S-R40][S-R41].
   - Interline/alliance agreements and IATA 735d [S-R48].
   - Published customer-service commitments, which DOT enforces [S-R19].
   - Corporate contracts.
4. **Operational feasibility**: available seats, MCT, airport curfews, crew.
5. **Commercial preference**: FFP tier, cabin, fare, CLV, ancillaries. Applies only within the space left by 1–4.

Commercial value never overrides levels 1–2 [STD per DOMAIN_RESEARCH_RULES]. The US explicitly allows fare and FFP status as DB factors, but requires the rules to avoid "unjust prejudice" [S-R11]. EU, UK, Canada and Brazil impose rights-based minimums that cannot be traded for loyalty benefits. EU261 Art. 15 excludes waiver, which the regulation's article list confirms [S-R02].

**5.2 Comparison of passenger-rights regimes** (verify before production; amounts as found 2026-11-20)

| Regime | Scope | Care thresholds | Rerouting / refund | Compensation | Extraordinary circumstances | Priority / special groups | Recent change |
|---|---|---|---|---|---|---|---|
| **EU261 (Reg. 261/2004), in force today** [STD] | Departures from EU; arrivals in EU on EU carriers | Meals/refreshments "in relation to waiting time"; hotel if overnight (Art. 9) | Art. 8: reimbursement, or rerouting at earliest opportunity / later date | €250 / €400 / €600 by distance (Art. 7). Delay ≥3 h at final destination (*Sturgeon* C-402/07, *Folkerts* C-11/11) | No compensation if unavoidable extraordinary circumstances. Care still due. Own-staff strike is **not** extraordinary (*Airhelp v SAS*, C-28/20, 23 Mar 2021) | Art. 11: priority carriage for PRM + companions/dogs and unaccompanied children; care ASAP | 2024 Commission Interpretative Guidelines C/2024/5687 [S-R08] |
| **EU revision – Reg. (EU) 2026/2202** (applies mainly from 23 Oct 2027) [STD][VALIDATE final OJ text] | As above; distance on whole journey | Refreshments every 2 h; meal after 3 h then every 5 h (max 3/day); internet + 2 calls; hotel if overnight (3-night cap in extraordinary circumstances, not for specific-needs groups) | Reimbursement offered at 5 h departure delay. Rerouting must consider other carriers/modes. No offer within 3 h → passenger may self-reroute, reimbursed ≤400 % of ticket within 14 days. Automatic refund within 7 days. Vouchers only with explicit consent | €250/€400/€600 kept. Trigger: >3 h arrival delay. 50 % reduction possible for >3,500 km journeys arriving ≤4 h late. Claims within 9 months. Info within 96 h | Art. 6c + non-exhaustive Annex (weather, ATC, hidden manufacturing defects, third-party strikes, etc.). Carrier bears burden of proving causal link and reasonable measures | Art. 11: PRM, disabled, pregnant, infants, UMNR, medical cases. Adjacent seat for companion free. Boarding priority; tarmac 2 h disembarkation (Art. 6a); missed connection rules (Art. 6b) | Adopted 16 Sep 2026; OJ 2 Oct 2026 [S-R04][S-R05][S-R06] |
| **UK261** (retained 261/2004) [STD] | Departures from UK; arrivals in UK on UK/EU carriers | As EU261 Art. 9 | As EU261 Art. 8 | £220 / £350 / £520 (Art. 7) | As EU261 case law pre-2021 | Art. 11 identical wording | CAA UK261 compliance programme from 2 Oct 2025; Civil Aviation Bill to give CAA fining powers; domestic compensation reform not finalised [S-R53] |
| **US DOT** [STD] | US carriers and foreign carriers at US airports | Tarmac: food/water by 2 h; deplane before 3 h domestic / 4 h international (14 CFR 259.4). No federal meal/hotel duty for delays (only carrier commitments) | Automatic cash refund on cancellation or significant change (≥3 h dom / ≥6 h intl) if passenger declines alternative (14 CFR 260). Refund within 7 business days (card) / 20 days (other) | **No delay/cancellation compensation rule**: ANPRM Dec 2024 withdrawn Nov 2025. IDB (14 CFR 250.5): 200 % of one-way fare up to $1,075 (1–2 h dom / 1–4 h intl late arrival); 400 % up to $2,150 beyond. Carriers may pay more | n/a for refunds (refund owed regardless of cause) | 250.3: carrier-defined priority rules may use check-in time, seat assignment, fare, FFP status, disability, UMNR status; no "unjust prejudice" | DBC limits revised 24 Oct 2024 (89 FR 84815; effective Jan 2025, enforcement delayed to 20 Mar 2025 [VALIDATE]). Renumbered-flight refund enforcement discretion to 7 Jul 2027 [S-R11–S-R18] |
| **Montreal Convention 1999** [STD] | International carriage between States Parties | – | – | Art. 19: carrier liable for **damage** caused by delay unless it took all reasonable measures. Proven loss, limited to 6,303 SDR per passenger (Art. 22(1); revised 28 Dec 2024, up from 5,346) | "All reasonable measures" defence | – | 2024 limit revision [S-R22][S-R23] |
| **Canada APPR** (SOR/2019-150) [STD] | Flights to, from and within Canada | Food/drink and communication after 2 h; hotel if overnight. Tarmac: disembark at 3 h (unless takeoff within 3 h 45 min) | Large carrier, controllable: own/partner within 9 h, else any carrier within 48 h, else nearby airport (s. 17(1)). Refund within 30 days | Delay (controllable, not safety): large carrier $400 (3–6 h) / $700 (6–9 h) / $1,000 (9 h+); small carrier $125/$250/$500 (s. 19). IDB $900/$1,800/$2,400 (s. 20) | Three-category scheme (controllable / controllable-safety / outside control). 2023 Act amendments put the onus on carriers to prove exceptional circumstances | **s. 15(4): order for IDB – UMNR → person with disability (+support) → families → previously denied.** Children <14 seated near guardian free (s. 22) | Regulations last amended 8 Sep 2022. Draft amendments in Canada Gazette I on 21 Dec 2024 (single "exceptional circumstances" model). **Final regulations not in force as of the data found** [S-R24–S-R28] [VALIDATE] |
| **India DGCA CAR Sec. 3 Series M Part IV** (Rev. 3, 27 Feb 2019 text seen) [STD] | Indian scheduled and non-scheduled operators; foreign carriers per home rules or CAR (para 3.5) | Meals by delay vs block time: ≥2 h (block ≤2.5 h), ≥3 h (2.5–5 h), ≥4 h (others). Hotel if delay >24 h or >6 h for 2000–0300 departures | Domestic delay >6 h: alternate within 6 h or full refund | Cancellation <2 weeks notice: INR 5,000 / 7,500 / 10,000 (or fare+fuel if less) by block time ≤1 h / 1–2 h / >2 h. IDB: none if alternate within 1 h; 200 % fare+fuel ≤INR 10,000 (alt within 24 h); 400 % ≤INR 20,000 (beyond 24 h or no alternate + refund) | Force majeure exempts compensation and some facilities | Para 3.7.2: particular attention to PRM needs. No explicit DB priority order found | A later revision (Rev. 4, reported effective 15 Feb 2023, downgrade refunds up to 75 %) **not verified from DGCA** [S-R29][S-R30] [VALIDATE] |
| **Brazil ANAC Res. 400/2016** [STD] | Domestic and international flights in Brazil | Art. 27: >1 h communication; >2 h food; >4 h hotel (if overnight) + transfer. PNAE hotel regardless of overnight | Art. 21: passenger chooses reaccommodation, refund or other mode if delay >4 h, cancellation, DB or carrier-caused missed connection. Art. 28: on own **or third-party** flight at first opportunity; refund within 7 days (Art. 29) | Art. 24: DB 250 DES domestic / 500 DES international, paid immediately. No fixed delay compensation (damages under consumer law) | Care continues even under force majeure (2026 update) | **Art. 28 sole para.: PNAE priority in reaccommodation. Reaccommodation precedes new sales** | ANAC Board approved amendments 22 Sep 2026 (information duties; temporary assistance modes in widespread events; reimbursement of documented care costs within 7 days). Effective 30 days after DOU publication [S-R31][S-R32] [VALIDATE] |
| **UAE GCAA CAR-PWP Issue 02** [STD] | Commercial air transport operators to/from or diverting to UAE airports; UAE airport operators | 1–3 h info; 3–8 h meals, communication, hotel for missed connections; >8 h hotel + transport | Return/rerouting on DB; on cancellation carriage "as soon as practicable", or rerouting on another airline subject to availability | **No fixed cash compensation** (the definition of "compensation" was removed in Issue 02). Damages via Commercial Transactions Law / Montreal | – | Volunteers first (GM2 PWP.B.002). No PRM priority order found in the CAR | Issue 02 applicable 1 Jan 2025. Dubai rules reported May 2026, details unverified [S-R33][S-R35] [VALIDATE] |
| **Saudi GACA Passenger Rights Protection Regs** [STD][VALIDATE] | Flights in and from KSA | Care by delay length | Alternative flight or refund | Reported: delay 50 SDR (≥3 h) / 150 SDR (≥6 h); cancellation up to 150 % of ticket; DB 200 % (press and secondary sources) | – | Reported exemption from overbooking DB for UMNR, first-degree family with domestic workers, groups, PRM | In force 20 Nov 2023 [S-R34] |
| **PRM: EC 1107/2006 / UK 1107** [STD] | EU (UK) airports and carriers | – | – | – | Safety-based refusal only (Art. 4) [VALIDATE wording] | No refusal on grounds of disability. Airport managing body provides assistance. 48 h pre-notification; carrier relays ≥36 h | Revised 2026/2202 amends 1107/2006 (PRM section) [S-R36][S-R07] |
| **PRM: US ACAA 14 CFR 382** [STD] | US and foreign carriers (US flights) | – | – | Wheelchair-mishandling remedies | – | Non-discrimination; assistance including connections | Wheelchair final rule 17 Dec 2024 (effective 16 Jan 2025). Enforcement of some provisions (382.125(e), 382.130(a), 382.132, 382.141(a)(6)) delayed to 31 Dec 2026; 5th Cir. challenge pending [S-R37] |

**5.3 Rules that directly constrain a prioritiser** [STD]
- **Mandated priority groups:**
  - PRM/UMNR priority (EU/UK Art. 11).
  - Canada's fixed IDB order (s. 15(4)).
  - PNAE priority in Brazil (Art. 28).
  - EU revision's protected group, whose accommodation is uncapped [S-R03][S-R24][S-R31][S-R04].
- **Escalation clocks force use of other carriers.** Canada 9 h → any carrier ≤48 h; EU revision 3 h → self-reroute at ≤400 %. ANAC permits third-party flights. In these jurisdictions a prioritiser that restricts itself to own metal can create liability [S-R24][S-R04][S-R31].
- **Volunteers first.** This applies in every regime reviewed: US 250.2b, EU Art. 4(1), Canada, DGCA 3.2.1, ANAC Art. 23, GCAA GM2 [S-R11][S-R24][S-R29][S-R31][S-R33].
- **Non-discrimination.** Priority based on disability is permitted or mandated *in favour* of PRM. Using disability *against* a passenger breaches ACAA/1107. US DB rules prohibit "unjust prejudice" [S-R11][S-R36][S-R37].
- **Refund cannot be replaced by a voucher without consent.** US 14 CFR 260; EU revision Art. 8a [S-R13][S-R04].

---

## 6. Industry practice & real-world cases

**6.1 Published denied-boarding priority rules (conditions of carriage)**
- **[SPECIFIC] Delta, International CoC Rule 21(C), updated 18 Aug 2026.** The order is:
  1. First/Business, Diamond/Platinum/Gold Medallion and corporate-agreement passengers before Coach.
  2. Passengers holding boarding passes.
  3. Among those without boarding passes: IROPS-rebooked passengers, then Silver Medallion, then SkyTeam Elite/Elite Plus, then non-elite.
  Within each group the order is class of service, then check-in time. Passengers with disabilities, UMNR, aged/infirm and military on orders may be accommodated irrespective of the order [S-R40].
  Rule 20: rebooking on Delta's next flight with seats in the purchased class. Other carriers only at Delta's discretion. Refund option at ≥360-minute changes [S-R40].
- **[SPECIFIC] Alaska Airlines CoC, revised 25 Aug 2026.** Confirmed seat assignment, then check-in time. Exceptions for UMNR, qualified individuals with a disability, and severe hardship ("business commitments will not, of themselves, constitute a severe hardship"). Accompanied children under 12 rank with their adult [S-R41].
- **[SPECIFIC] Breeze, CoC 20 Mar 2025.** Fare class and booking type, itinerary, loyalty status, check-in time, seat-assignment time [S-R42].
- **[PRACTICE]** Across US CoCs the common factors are fare/class, check-in time, elite status, and protection of UMNR/PRM. A non-US full-service carrier's published equivalent was not retrieved **[VALIDATE]**.

**6.2 Vendor products that rank or value passengers**
- **[SPECIFIC] Amadeus Passenger Recovery** claims to:
  - "Prioritize the rebooking of high-value passengers."
  - Use recovery templates "based on individual traits and policies".
  - Balance seat sales against reaccommodation obligations.
  [S-R43] An Amadeus infographic lists optimiser inputs (rebooking and overnight cost, merchandising, passenger revenue, passenger value, loyalty score) [S-R45]. These are vendor marketing claims; the weighting logic is not public.
- **[SPECIFIC] Air Canada with Amadeus Passenger Recovery** (Amadeus blog, 17 Oct 2024):
  - ~90 % auto-proposals; average about 10 minutes from cancellation notice to rebooking.
  - Previously 45 min to 12 h per cancelled flight.
  - Bilateral partner agreements are used to limit cost.
  - Logic for "customers with disabilities and premium customers" was *planned*, not live [S-R44].
  This is notable because APPR mandates disability priority for IDB [S-R24].
- **[SPECIFIC] Sabre IROPS Reaccommodation** "notifies, prioritizes and reaccommodates customers based on value" using airline business rules [S-R46]. A ~2009 Business Travel News report describes SabreSonic's customer-value score as using purchase history, total revenue and *past service disruptions* [S-R47]. This is dated; treat as historical.
- **[PRACTICE]** IATA Res. 735d governs interline involuntary rerouting among IATA members/MITA participants. LCCs that are not IATA members are excluded from 735d alternatives [S-R48].

**6.3 Enforcement cases showing where reaccommodation failure costs most**
- **[SPECIFIC] Southwest Airlines, Dec 2022 meltdown.** DOT Order 2023-12-11 (18 Dec 2023) assessed a $140 M penalty for failures in refunds, notifications and customer service. More than $600 M had already gone to passengers in refunds and reimbursements; total >$750 M. The order was amended 5 Dec 2025, crediting the remaining $11 M [S-R20].
- **[SPECIFIC] Delta, CrowdStrike outage, July 2024.** DOT opened a probe citing "customer service failures". It was closed in June 2026 without penalty, the government concluding that passengers were adequately compensated [S-R21].
- **[STD] US customer-service dashboard.** Commitments (e.g. rebooking on a partner at no cost for controllable cancellations) become enforceable once published. Allegiant and Spirit do not commit to partner rebooking [S-R19].

---

## 7. AI/technology approaches and opportunities

**7.1 Where rules suffice (do not use ML)**
- **[STD]/[PRACTICE]** Regime applicability, entitlements, clocks, compensation amounts and mandated priority groups are deterministic. They belong in a versioned rules engine or decision tables with legal sign-off and effective dating, e.g. EU 261 → 2026/2202 switching on 23 Oct 2027.
- **[PRACTICE]** Published DB priority orders (Delta, Alaska, Canada s. 15(4)) are lexicographic sorts and need no learning.

**7.2 Where optimisation is proven** [SPECIFIC][ACADEMIC]
- Network-wide seat allocation across own, partner and interline inventory is an assignment/flow problem. Vendors run it in production: Amadeus reports "solution found for all passengers within 70 minutes" (marketing) [S-R45]; Air Canada reports ~90 % automation [S-R44].
- The academic literature covers integrated aircraft and passenger recovery, passenger-response models (Cadarso & Vaze, *Transportation Science* 2023 [S-R49]), pre-emptive rerouting under uncertain delays [S-R51], and a 2024 review of passenger-oriented recovery [S-R50].
- The literature mostly minimises cost plus passenger delay. Explicit fairness or legal-tier constraints are rarely modelled. No published equity-constrained reaccommodation model was found in this pass **[VALIDATE: deeper search]**.

**7.3 Proposed scoring structure** ([AI-OPP], synthesised here; not an industry standard)
1. **Tier 0 – feasibility filters (hard):**
   - Safety/acceptance (PRM numbers, medical clearance).
   - Visa/transit.
   - MCT.
   - Comparable transport conditions.
   - Passenger choice already made (refund vs rerouting).
2. **Tier 1 – legally mandated priority (lexicographic):**
   - Jurisdiction-specific order. Canada: UMNR > disability > families > previously denied. EU/UK: PRM, UMNR (+ the 2026/2202 group). Brazil: PNAE.
   - Then passengers whose legal clock is closest to expiring: Canada's 9 h/48 h, EU's 3 h offer, overnight thresholds.
3. **Tier 2 – operational urgency:**
   - Last frequency of the day; overnight hotel avoidance.
   - Protected onward connections (married segments, final destination).
   - Number of remaining segments at risk.
   - Group/family integrity.
4. **Tier 3 – weighted score (tie-breaker only within a tier).** Configurable weights over:
   - Arrival delay at final destination (passenger inconvenience).
   - Expected regulatory cost (compensation + care); see the caution below.
   - Contractual commitments (corporate SLA, FFP benefits written into terms).
   - Cabin/fare.
   - FFP tier / CLV.
   - "Already disrupted recently" uplift (fairness / recovery equity, cf. SabreSonic's use of past disruptions [S-R47]).
5. **Tier 4 – deterministic tie-break.** Check-in time or booking time, which is US-recognised [S-R11]. This keeps results reproducible.

Using "expected compensation cost" as a weight has a cost-minimising bias. It may push passengers with *lower* legal entitlements (e.g. short-haul, US-origin) to the back systematically. Treat this as a fairness risk to review, not a free optimisation lever **[VALIDATE with legal]**.

**7.4 ML/GenAI opportunities, with maturity** [AI-OPP]
- **Predict acceptance of offered alternatives** (choice models) to reduce re-rebooking churn. Research exists [S-R49]; production evidence is vendor-claimed only.
- **Predict missed connections early**, so passengers are protected before inventory runs out. Air Canada does day-before delay handling [S-R44]. See note 03.
- **Infer unflagged special needs**, e.g. an infant from the date of birth. *Do not* infer health or disability from behaviour: privacy and discrimination risk.
- **LLM explanations and agent assist.** Generate a passenger-facing reason for each offer, plus an agent-facing rationale citing the rule and tier. This supports GDPR Art. 22 transparency [S-R39]. Not proven in production in public sources.
- **Self-service re-ranking.** Show passengers alternatives ordered by their own stated preference. Self-service is in production at Amadeus/Air France; preference learning is research-level [S-R43].

---

## 8. Risks

**Legal**
- **[STD]** Mis-ordering mandated groups breaches EU Art. 11 / APPR s. 15(4) / ANAC Art. 28, and ACAA/1107 if disability is used to a passenger's detriment [S-R03][S-R24][S-R31][S-R36][S-R37].
- **[STD]** EU revision: failure to offer comparable rerouting within 3 h exposes the carrier to self-rerouting costs up to 400 % of the fare [S-R04]. A commercially-ranked queue that leaves low-value passengers unserved for >3 h is directly costly.
- **[STD]** US: published commitments and boarding-priority rules are enforceable. Deviation from one's own CoC is an unfair/deceptive practice risk [S-R11][S-R19].
- **[STD]** GDPR:
  - Art. 9 lawful basis for health SSRs.
  - Art. 22 if ranking is solely automated with significant effects. SCHUFA extends this to scores that play a determining role [S-R38][S-R39].
  - DPIA likely needed for large-scale profiling **[VALIDATE]**.
  - Whether the EU AI Act (Reg. (EU) 2024/1689) classes passenger ranking as high-risk was **not researched** **[VALIDATE]**.
- **[VALIDATE]** Multi-regime itineraries: priority for an EU261-covered passenger vs a non-covered passenger on the same constrained flight. Legal exposure differs, and favouring the legally "expensive" passenger may itself be a fairness or reputational issue.

**Fairness / ethics**
- **[ACADEMIC]/[AI-OPP]** CLV and fare correlate with income, corporate employment and nationality/route. Ranking on them reproduces socioeconomic disparities in who is stranded overnight. Proxies such as booking channel and postcode can introduce indirect discrimination **[VALIDATE]**.
- **[PRACTICE]** A transparency gap: most airlines do not publish *rebooking* priority (as distinct from DB priority).

**Reputational**
- **[SPECIFIC]** Mass-disruption failures (Southwest 2022, Delta 2024) brought regulatory probes and penalties [S-R20][S-R21]. Visible "elite first, families stranded" stories carry outsized brand risk **[VALIDATE]**.

**Airline-model differences** [PRACTICE][VALIDATE]
- **Full-service/hub carriers**: rich FFP/corporate data, alliances and interline (735d) give large alternative pools. Commercial tiers are common (Delta).
- **LCCs**: often no interline or 735d, so the pool is limited to own metal. That increases legal exposure where rules force other-carrier rerouting (EU revision, Canada large carriers). Priority tends to be simpler (Alaska/Breeze-style check-in or seat order). Spirit and Allegiant do not commit to partner rebooking [S-R19].
- **Regional carriers**: Canada's small-carrier tier has lower compensation and no fixed rebooking window [S-R24]. Capacity-purchase partners operate under the mainline brand's rules.
- **Gulf hub carriers**: UAE PWP has care duties but no fixed cash compensation. Large transfer flows mean that connection protection dominates [S-R33].

---

## 9. Open questions / knowledge gaps / items to validate with an airline

1. **Final OJ text of Reg. (EU) 2026/2202.** Confirm article numbering, the 3 h rerouting/400 % self-rerouting rule, the Art. 11 groups and the application date of 23 Oct 2027. The analysis used the 16 Jun 2026 joint text before legal-linguistic revision [S-R04].
2. **Canada.** Have the Dec 2024 draft APPR amendments been finalised after June/Oct 2026? The consolidation shows no amendment since 2022 [S-R24][S-R28].
3. **India.** Obtain the current DGCA CAR M-IV revision from dgca.gov.in (Rev. 4/2023 and any 2025–26 drafts). Amounts here are from Rev. 3 (2019) [S-R29][S-R30].
4. **Brazil.** Publication date and text of the Sept 2026 Res. 400 amendment; whether DB compensation (250/500 DES) or the PNAE priority changed [S-R32].
5. **Saudi GACA.** Read the regulation text (the PDF fetch failed); amounts are from secondary sources. UAE/Dubai 2026 rules [S-R34][S-R35].
6. **US.** Current DBC dollar limits after the 2025 enforcement delay; any 2026 DOT refund-rule amendments; status of the wheelchair-rule litigation and enforcement delay past 31 Dec 2026 [S-R12][S-R15][S-R37].
7. **EC 1107/2006 Art. 4.** Exact refusal wording was not retrieved [S-R36].
8. **Airline internal policy.**
   - The *rebooking* (not DB) priority order.
   - Whether FFP/CLV is used and who may override.
   - Corporate-contract SLAs.
   - Alliance/JV reaccommodation agreements.
   - How PRM/UMNR are flagged in the airline's PSS.
9. **Data.** Availability and quality of CLV, pregnancy/medical flags and group links; GDPR lawful basis and retention.
10. **Fairness metrics.** Which distributional KPIs (e.g. overnight-stranding rate by fare/tier/route) the airline will accept or report.
11. **Non-US full-service and Gulf carrier CoCs.** Published DB priority not retrieved in this pass. United's Rule 25 page timed out.

---

## 10. Sources

| ID | Tier | Title | Publisher / author | Publication date | URL | Accessed | What it supports |
|---|---|---|---|---|---|---|---|
| S-R01 | 1 | Regulation (EC) No 261/2004 | EU (EUR-Lex) | 11 Feb 2004 | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32004R0261 | 2026-11-20 (fetch failed; content verified via S-R02/S-R03 and S-R04) | EU261 structure Arts 4–11 |
| S-R02 | 1 | Regulation (EC) No 261/2004 (UK retained), Art. 7 and contents | legislation.gov.uk | current version | https://www.legislation.gov.uk/eur/2004/261/article/7 | 2026-11-20 | UK261 £220/£350/£520; article list incl. Art. 15 |
| S-R03 | 1 | Reg. 261/2004 Art. 11 (UK retained) | legislation.gov.uk | current version | https://www.legislation.gov.uk/eur/2004/261/article/11 | 2026-11-20 | Priority for PRM and unaccompanied children |
| S-R04 | 1 | PE-CONS 39/26 – Joint text amending Reg. 261/2004 and 2027/97 | European Parliament & Council | 16 Jun 2026 | https://data.consilium.europa.eu/doc/document/PE-39-2026-INIT/en/pdf | 2026-11-20 | Revised Arts 6, 6a, 6b, 6c, 7, 8, 8a, 9, 11; Annex; 12-month application |
| S-R05 | 1 | Regulation (EU) 2026/2202 (OJ L) | EUR-Lex | 2 Oct 2026 | https://eur-lex.europa.eu/eli/reg/2026/2202/oj | 2026-11-20 (via search index; not opened) | Publication, entry into force 22 Oct 2026 |
| S-R06 | 2 | Evolution delivered: what Regulation (EU) 2026/2202 means for EU261 reform | Burges Salmon (Bettle, Challinor, Bourne) | 8 Oct 2026 | https://www.burges-salmon.com/articles/102o4ut/evolution-delivered-what-regulation-eu-2026-2202-means-for-eu261-reform | 2026-11-20 | Adoption 16 Sep 2026; application 23 Oct 2027; content summary |
| S-R07 | 2 | New European Regulation on Air Passenger Rights | CMS (Lepièce, Willems) | 25 Jun 2026 (mod. 8 Oct 2026) | https://cms.law/en/gbr/legal-updates/new-european-regulation-on-air-passenger-rights-what-impact-for-the-air-transport-sector | 2026-11-20 | Political agreement 15 Jun 2026; PRM section amends 1107/2006 |
| S-R08 | 1 | Commission Interpretative Guidelines on Reg. 261/2004 (C/2024/5687) | European Commission | 25 Sep 2024 | https://eur-lex.europa.eu/eli/C/2024/5687/oj/eng | 2026-11-20 (search only) | Current EU guidance |
| S-R09 | 1/2 | CJEU case law (Sturgeon C-402/07, 19 Nov 2009; Folkerts C-11/11, 26 Feb 2013; Wallentin-Hermann C-549/07, 22 Dec 2008) | CJEU; summaries via search | various | https://curia.europa.eu | 2026-11-20 | 3 h delay compensation; final-destination delay; extraordinary-circumstances test (judgment dates from reviewer knowledge [VALIDATE]) |
| S-R10 | 2 | Air passenger rights: a staff strike is not an "extraordinary circumstance" | CMS | 2021 | https://cms.law/en/aut/legal-updates/air-passenger-rights-a-staff-strike-is-not-an-extraordinary-circumstance-to-avoid-compensation-to-passengers | 2026-11-20 | Airhelp v SAS C-28/20, 23 Mar 2021 |
| S-R11 | 1 | 14 CFR Part 250 (§§250.2b, 250.3, 250.5) | Cornell LII (eCFR text) | amended to 89 FR 84818 (24 Oct 2024) | https://www.law.cornell.edu/cfr/text/14/250.3 ; https://www.law.cornell.edu/cfr/text/14/250.5 | 2026-11-20 | DB priority factors; DBC 200 %/400 %, $1,075/$2,150 |
| S-R12 | 1 | Periodic Revisions to DBC and Domestic Baggage Liability Limits (89 FR 84815); delay notice (90 FR, 20 Feb 2025) | DOT / Federal Register | 24 Oct 2024; 20 Feb 2025 | https://www.govinfo.gov/content/pkg/FR-2024-10-24/html/2024-23588.htm | 2026-11-20 | DBC revision, effective Jan 2025, enforcement delayed to 20 Mar 2025 |
| S-R13 | 1 | Refunds and Other Consumer Protections, final rule (89 FR 32760) | DOT / Federal Register | 26 Apr 2024 | https://www.federalregister.gov/documents/2024/04/26/2024-07177/refunds-and-other-consumer-protections | 2026-11-20 | 14 CFR 260 automatic refunds; significant change 3 h/6 h |
| S-R14 | 1 | What airline passengers need to know about DOT's automatic refund rule | DOT | 2024 | https://www.transportation.gov/briefing-room/what-airline-passengers-need-know-about-dots-automatic-refund-rule | 2026-11-20 | Refund timing 7 business / 20 calendar days |
| S-R15 | 1 | Enforcement discretion notice – renumbered flights (FR 2026-13675) | DOT / Federal Register | 7 Jul 2026 | https://www.govinfo.gov/content/pkg/FR-2026-07-07/html/2026-13675.htm | 2026-11-20 | Discretion extended to 7 Jul 2027 |
| S-R16 | 1 | 14 CFR 259.4 Tarmac delay contingency plans | Cornell LII | 86 FR 23270, 3 May 2021 | https://www.law.cornell.edu/cfr/text/14/259.4 | 2026-11-20 | 3 h/4 h tarmac limits; food/water at 2 h |
| S-R17 | 4 | Flight disruption reimbursement rule canceled by Trump administration; DOT ditches rule (Washington Times) | Axios; Washington Times | 4 Sep 2025; 17 Nov 2025 | https://www.axios.com/2025/09/04/trump-transportation-airline-consumer-protections ; https://m.washingtontimes.com/news/2025/nov/17/transportation-department-ditches-rule-require-airlines-pay/ | 2026-11-20 | Compensation rulemaking abandoned and withdrawn (FR citation not verified) |
| S-R18 | 1 | ANPRM Airline Passenger Rights (2105-AF20) | DOT | Dec 2024 | https://www.transportation.gov/sites/dot.gov/files/2024-12/ANPRM%20Airline%20Passenger%20Rights%20%282105-AF20%29.pdf | 2026-11-20 | Original compensation proposal |
| S-R19 | 1 | Airline Customer Service Dashboard | DOT | live page | https://www.transportation.gov/airconsumer/airline-customer-service-dashboard | 2026-11-20 | Partner rebooking commitments; enforceability; carrier variation |
| S-R20 | 1 | DOT penalizes Southwest Airlines $140 million; Order 2025-12-4 | DOT | 18 Dec 2023; 5 Dec 2025 | https://www.transportation.gov/briefing-room/dot-penalizes-southwest-airlines-140-million-2022-holiday-meltdown | 2026-11-20 | Case: reaccommodation/refund failure penalty |
| S-R21 | 4 | DOT drops investigation of Delta for CrowdStrike outage | Atlanta Journal-Constitution (and Reuters via search) | Jun 2026 | https://www.ajc.com/business/2026/06/dot-drops-investigation-of-delta-for-crowdstrike-outage/ | 2026-11-20 | Case: probe opened Jul 2024, closed Jun 2026 |
| S-R22 | 1 | 2024 Revised Limits of Liability under the Montreal Convention 1999 | ICAO | 2024 | https://www.icao.int/sites/default/files/secretariat/legal/LEB%20Treaty%20Collection%20Documents/2024_Revised_Limits_of_Liability_Under_the_Montreal_Convention_of_1999_en.pdf | 2026-11-20 (via search; corroborated by CTA) | 6,303 SDR delay limit from 28 Dec 2024 |
| S-R23 | 1 | Convention for the Unification of Certain Rules for International Carriage by Air (Montreal 1999) | ICAO | 1999 | https://www.icao.int/sites/default/files/secretariat/legal/Administrative%20Packages/mtl99_en.pdf | 2026-11-20 (not opened) | Art. 19 delay liability |
| S-R24 | 1 | Air Passenger Protection Regulations SOR/2019-150 | Justice Laws Canada | current to 29 Oct 2026; last amended 8 Sep 2022 | https://laws.justice.gc.ca/eng/regulations/SOR-2019-150/FullText.html | 2026-11-20 | s. 15(4) priority; s. 17 rebooking; s. 19/20 compensation; care; tarmac; child seating |
| S-R25 | 1 | Regulations Amending the APPR (proposed), Canada Gazette I Vol. 158 No. 51 | Government of Canada | 21 Dec 2024 | https://gazette.gc.ca/rp-pr/p1/2024/2024-12-21/html/reg1-eng.html | 2026-11-20 (search only) | Draft amendments |
| S-R26 | 1 | Strengthening Air Passenger Protection in Canada | Canadian Transportation Agency | n.d. | https://otc-cta.gc.ca/eng/strengthening-air-passenger-protection-canada | 2026-11-20 (search only) | Onus on carriers (2023 Act amendments) |
| S-R27 | 2 | Preparing for takeoff: the amended APPR | Fasken | Jul 2025 | https://www.fasken.com/en/knowledge/2025/07/preparing-for-takeoff-the-amended-air-passenger-protection-regulations | 2026-11-20 (search only) | Status pending |
| S-R28 | 4 | Enact new protections for passengers (press release) | Option consommateurs | Feb 2026 | https://option-consommateurs.org/en/press-releases/enact-new-protections-passenger | 2026-11-20 (search only) | Amendments still not in force (Feb 2026) |
| S-R29 | 1 (mirror) | DGCA CAR Section 3 Series M Part IV, Issue I (2010), Rev. 3 | DGCA India (copy hosted by livefromalounge.com) | 27 Feb 2019 | https://livefromalounge.com/wp-content/uploads/2023/12/D3M-M4-1.pdf | 2026-11-20 | DB 200 %/400 % caps; cancellation INR amounts; delay facilities |
| S-R30 | 4 | DGCA Passenger Rights in India (2026); DGCA downgrade-refund reports | Wego blog; Lokmat | 2026; n.d. | https://blog.wego.com/dgca-passenger-rights/ | 2026-11-20 (search only) | Reported Rev. 4 (15 Feb 2023); unverified |
| S-R31 | 1 (mirror) | Resolução ANAC nº 400, de 13 de dezembro de 2016 | ANAC (copy hosted by Procon Goiás) | DOU 14 Dec 2016 | https://goias.gov.br/procon/wp-content/uploads/sites/19/2017/03/resolucao-400-anac.pdf | 2026-11-20 | Arts 21, 23, 24, 27, 28 (PNAE priority), 29 |
| S-R32 | 1 | ANAC atualiza regras sobre atrasos e cancelamentos | Agência Gov (EBC) | 22 Sep 2026 | https://agenciagov.ebc.com.br/noticias/202609/anac-atualiza-regras-sobre-atrasos-e-cancelamentos-e-amplia-deveres-de-informacao-aos-passageiros | 2026-11-20 | 2026 amendment of Res. 400 |
| S-R33 | 1 | CAR-PWP Passenger Welfare Program, Issue 02 | UAE GCAA | issued 25 Dec 2024; applicable 1 Jan 2025 | https://www.gcaa.gov.ae/en/epublication/EPublications/Civil%20Aviation%20Regulations%20(CARs)/CAR%20III%20-%20GENERAL%20REGULATIONS/CAR-PWP%20-%20PASSENGER%20WELFARE%20PROGRAM%20-%20ISSUE%2002.pdf | 2026-11-20 | UAE scope, care thresholds, no fixed compensation |
| S-R34 | 1/4 | New Saudi passenger rights rules take effect; Know Your Rights guide; AirHelp summary | GACA; AirHelp | 20 Nov 2023; n.d. | https://gaca.gov.sa/web/en-gb/news/20-nov-2023 ; https://gaca.gov.sa/-/media/Files/PDF/Content--Pages/Know-your-rights-En.pdf | 2026-11-20 (search only; regulation PDF failed) | Saudi regime (amounts [VALIDATE]) |
| S-R35 | 4 | Dubai Strengthens Passenger Rights Rules | Skift | 5 May 2026 | https://skift.com/2026/05/05/dubai-strengthens-passenger-rights-rules-to-rebuild-traveler-trust/ | 2026-11-20 (search only) | Dubai 2026 rules; details unknown |
| S-R36 | 1 | Regulation (EC) No 1107/2006; CAA guidance | EUR-Lex; legislation.gov.uk; UK CAA | 5 Jul 2006 | https://eur-lex.europa.eu/eli/reg/2006/1107/oj | 2026-11-20 (search only) | PRM non-refusal; 48 h notice; airport responsibility; 36 h relay |
| S-R37 | 1 | Ensuring Safe Accommodations for Air Travelers With Disabilities Using Wheelchairs (89 FR 102398); enforcement notices | DOT / Federal Register | 17 Dec 2024; 10 Jun 2025; 30 Sep 2025 | https://www.federalregister.gov/documents/2024/12/17/2024-29731/ensuring-safe-accommodations-for-air-travelers-with-disabilities-using-wheelchairs | 2026-11-20 (search only) | ACAA wheelchair rule, enforcement delay to 31 Dec 2026 |
| S-R38 | 1 | Regulation (EU) 2016/679 (GDPR), Arts 4, 9, 22 | EUR-Lex | 27 Apr 2016 | https://eur-lex.europa.eu/eli/reg/2016/679/oj | 2026-11-20 (not opened; standard text) | Special-category data; automated decisions |
| S-R39 | 1/2 | CJEU C-634/21 SCHUFA Holding (Scoring); IAPP takeaways | CJEU; IAPP | 7 Dec 2023 | https://iapp.org/news/a/key-takeaways-from-the-cjeus-recent-automated-decision-making-rulings | 2026-11-20 (search only) | Score as Art. 22 decision |
| S-R40 | 1 (airline) | Delta Contract of Carriage – International (Rules 20, 21) | Delta Air Lines | last update 18 Aug 2026 | https://www.delta.com/us/en/legal/contract-of-carriage-igr | 2026-11-20 | Commercial DB priority tiers; rebooking on other carriers |
| S-R41 | 1 (airline) | Alaska Airlines Contract of Carriage | Alaska Airlines | revised 25 Aug 2026 | https://resource.alaskaair.net/v3/assets/blt2cefe12c88e9dd91/blta6d545d0295aad57/CoC%20English | 2026-11-20 | Seat/check-in DB priority; hardship exceptions |
| S-R42 | 1 (airline) | Breeze Airways Contract of Carriage | Breeze Airways | 20 Mar 2025 | https://media.flybreeze.com/docs/policies/contractofcarriage.pdf | 2026-11-20 (search excerpt) | DB factors incl. loyalty status |
| S-R43 | 2 | Amadeus Passenger Recovery (product page) | Amadeus | undated | https://amadeus.com/en/portfolio/airlines/passenger-recovery | 2026-11-20 | Value-based prioritisation claims |
| S-R44 | 2 | How Amadeus helps Air Canada rebook disrupted passengers in just 10 minutes | Amadeus (N. Chamelian, Air Canada) | 17 Oct 2024 | https://amadeus.com/en/blog/articles/how-amadeus-helps-air-canada-rebook-disrupted-passengers-in-just-10-minutes | 2026-11-20 | 90 % automation; planned PRM/premium logic |
| S-R45 | 2 | Amadeus Disruption Management (infographic) | Amadeus | undated | https://amadeus.com/content/dam/amadeuswebevo/brand/amadeus/infographics/amadeus-disruption-management.pdf | 2026-11-20 (search excerpt) | Optimiser inputs incl. passenger value, loyalty score |
| S-R46 | 2 | Airline recovery with IROPS Reaccommodation | Sabre | undated | https://sabre.com/?p=20192 | 2026-11-20 (search excerpt) | Value-based prioritisation claim |
| S-R47 | 4 | Some Airlines Begin To Use New Tools To Re-Accommodate Passengers | Business Travel News | c. 2009 [VALIDATE date] | https://www.businesstravelnews.com/Technology/Some-Airlines-Begin-To-Use-New-Tools-To-Re-Accommodate-Passengers/12798 | 2026-11-20 (search excerpt) | SabreSonic value score incl. past disruptions (historical) |
| S-R48 | 1 | Guidance document – Interline considerations on IROPS | IATA | 25 Jun 2020 | https://www.iata.org/contentassets/e7a533819be440edbb1e49da96e0f2a8/guidance-document-interline-irops_25june2020.pdf | 2026-11-20 (search excerpt) | Res. 735d scope and limits |
| S-R49 | 3 | Passenger-Centric Integrated Airline Schedule and Aircraft Recovery | Cadarso & Vaze, *Transportation Science* 57(3) | 2023 | https://pubsonline.informs.org/doi/10.1287/trsc.2022.1174 | 2026-11-20 (abstract via search) | Passenger response in recovery optimisation |
| S-R50 | 3 | Passenger-oriented airline recovery review (arXiv 2401.04866) | arXiv | Jan 2024 | https://arxiv.org/pdf/2401.04866 | 2026-11-20 (search excerpt) | Literature overview |
| S-R51 | 3 | Preemptive rerouting of airline passengers under uncertain delays | *Computers & Operations Research* (ScienceDirect) | c. 2018 [VALIDATE] | https://www.sciencedirect.com/science/article/abs/pii/S0305054817302253 | 2026-11-20 (abstract via search) | Stochastic pre-emptive rebooking |
| S-R52 | 3 | Joint aircraft and passenger recovery (TRE 2016, Univ. of Iowa host) | Univ. of Iowa faculty page | 2016 | https://www.biz.uiowa.edu/faculty/kangzhao/pub/TRE_2016.pdf | 2026-11-20 (search excerpt) | Academic priority ordering (VIP flights first) |
| S-R53 | 1 | UK261 compliance programme; DfT aviation consumer policy reform consultation response | UK CAA; DfT | 2 Oct 2025; n.d. | https://www.caa.co.uk/air-passengers/travel-problems-and-rights/airline-and-travel-company-problems/enforcement-action/uk261-compliance-programme-into-air-passenger-rights/ | 2026-11-20 (search only) | UK enforcement changes; domestic reform not finalised |

**Source count:** 53 IDs (S-R01–S-R53).
**Verification depth:**
- Opened and read directly: S-R02, 03, 04, 06, 07, 11, 16, 24, 29, 31, 32, 33, 40, 41, 43, 44.
- Others were verified through search excerpts or secondary corroboration and are marked accordingly.

**Conflicts flagged:**
- EU revision dates: CMS (June) predates adoption. Claims sites gave a Council approval date of 13 Jul 2026, while Burges Salmon gives formal adoption on 16 Sep 2026. S-R05 and S-R06 are preferred.
- India: DGCA Rev. 3 (2019) vs a reported Rev. 4 (2023).
- Saudi: how the 150 % cancellation compensation applies (GACA guide vs SkyRefund).
- CTA transition book: a draft-amendment date of Dec 2025 vs the Gazette's 21 Dec 2024.
