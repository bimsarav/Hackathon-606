# 03 — Passenger Impact Assessment (MASTER_PROMPT §15.7.3)

> Part of topic `disruption-management`. Research question: *how can AI help an airline predict, assess and minimise the impact of flight disruptions on its network and passengers?* This note covers the **passenger side**: PSS data, PNR/ticket structures, connections and MCT, inventory, re-accommodation rules, special needs, ancillaries, notification and passenger-centric metrics.
> Researched 2026-11-20. Sources are listed in §10.
> Labels: `[STD]` standard/regulation · `[PRACTICE]` common industry practice · `[SPECIFIC]` one airline/vendor · `[ACADEMIC]` research · `[AI-OPP]` potential AI improvement · `[VALIDATE]` confirm with an airline or primary text.
> Related notes (same folder): [00-OVERVIEW](00-OVERVIEW.md) · [01 prediction](01-disruption-prediction.md) · [02 network impact & recovery](02-network-impact-and-recovery.md) · [03 passenger impact](03-passenger-impact.md) · [04 prioritisation & rights](04-passenger-prioritization-and-rights.md) · [05 OCC/PCU & systems](05-occ-pcu-workflows-and-systems.md). Sources: [`../../SOURCES.md`](../../SOURCES.md) (IDs are namespaced per note and final; no renumbering). Glossary: [`../../GLOSSARY.md`](../../GLOSSARY.md).

---

## 1. Key findings

1. **[STD]** IATA defines an *involuntary reroute* under **Resolution 735d** (Involuntary Change of Carrier, Routing, Class or Type of Fare). It applies when "the circumstance has not occurred earlier than one day prior to the scheduled departure time of the first impacted flight". Earlier changes are *planned schedule changes*, covered by **Recommended Practice 1735**. This one-day boundary decides the ticketing, billing and passenger-handling workflow, so a system has to classify each event before it acts [S-X01].
2. **[STD]** Involuntary reissue rules are precise and machine-checkable:
   - "INVOL" goes in the first 5 characters of the endorsement box.
   - Only the impacted coupons are reissued.
   - The fare basis and the baggage allowance are those of the *first affected coupon*.
   - Control of a coupon is requested with an "involuntary" indicator.
   - In billing, an INVOL designation counts only for reissues **≤ 2 days** from the first scheduled departure. It is invalid for coupons departing **≥ 5 days** after the reissue date (the RAM "2-day / 5-day rules").

   These are deterministic rules; they need no AI [S-X01].
3. **[STD]** The **delivering carrier** is responsible for a misconnecting interline passenger: it cancels the onward space that can no longer be used and rebooks the passenger (Res 766). Inventory on another carrier needs a bilateral agreement or direct contact first (e.g. the AIRIMP 3.18 "NI" action code). Upgrading to a higher cabin on the new carrier is not allowed unless bilaterally agreed [S-X01].
4. **[STD]** Ancillaries break during a reroute. Prepaid bags on an **EMD-A** must either be re-associated to the new coupon or be written into the reissued ticket's baggage allowance. Under **RP 1790**, other additional services (seats, meals, etc.) are *not* rerouted onto other carriers unless bilaterally agreed; otherwise they are refunded under the carrier's conditions of carriage [S-X01]. EMDs are defined in **Res 725f/g/h** [S-X01][S-X31].
5. **[STD]** Minimum Connecting Times are an IATA standard (**SSIM Chapter 8**), maintained by the Minimum Connecting Times Group under the Passenger Standards Conference. The data comprises station standards (status DD/DI/ID/II) plus *exceptions* by carrier, codeshare, flight-number range, terminal, aircraft type, and *suppressions*. MCT is an itinerary-legality rule, not a prediction of whether a passenger will actually make the connection [S-X02][S-X03].
6. **[ACADEMIC]** Flight-centric metrics understate what passengers experience. MIT work on the US system attributes about **48–50 % of passenger delay minutes to cancellations and missed connections** (2015 breakdown: 52 % flight delay, 29 % cancellations, 19 % missed connections), although these events are rare at flight level [S-X40][S-X41][S-X42]. This is the strongest argument for assessing impact at **PNR/journey level**.
7. **[SPECIFIC]** Automated re-accommodation runs in production. All of the figures below are vendor- or airline-reported and have not been independently audited [VALIDATE]:
   - **Air Canada** with Amadeus Passenger Recovery: about **90 %** of cancellation handling automated, an average of **10 min** from cancellation notice to rebooking, and more than 1 M passengers re-accommodated per year [S-X12].
   - **SWISS** is cited as the first airline to deploy the product; it rebooks about 150 k passengers per year [S-X13].
   - **Sabre IROPS Reaccommodation** rescheduled more than 500 k PNRs in March 2020 [S-X17].
8. **[SPECIFIC]** Self-service rebooking is mainstream at large carriers.
   - **United** (June 2023): app and web rebooking options, plus meal, hotel and rideshare vouchers, shown for delays over 60 min or cancellations. United says nearly 50 % of its customers already self-serve during disruptions [S-X37].
   - **American Airlines** offers a similar app flow [S-X45].
   - **Finnair** and **Air France** are named users of Amadeus Self Re-accommodation [S-X14].
9. **[STD]** Passenger-rights regimes are hard constraints on any optimiser.
   - **EU 261/2004:** Art. 8 gives a re-routing choice. Art. 11 gives *priority* to persons with reduced mobility (PRMs), their companions and service dogs, and unaccompanied children. Art. 14 requires written notice of rights on denied boarding, cancellation or a delay of 2 h or more [S-X34].
   - **US DOT automatic refund rule:** in effect from 28 Oct 2024. A "significant change" is 3+ h domestic or 6+ h international, or a change of airport [S-X36].
10. **[PRACTICE]** Today's PNR cannot represent non-homogeneous itineraries, so rebooking part of a party forces a **PNR split**. NDC's Order model, and later ONE Order, removes this constraint and adds machine-readable involuntary-change notifications to sellers (OrderChangeNotif, from NDC 17.2/19.2). Adoption is still partial, and interline/disruption servicing is the weakest area [S-X08][S-X52][S-X09].
11. **[AI-OPP]** The most defensible AI uses are these:
    - (a) **Probabilistic connection-risk prediction** per passenger, beyond static MCT. This has been proven in research and in a Heathrow prototype [S-X43][S-X44].
    - (b) **Passenger-choice and acceptance prediction** for self-service offers.
    - (c) **Ranking and explaining options inside an optimisation solver.**

    Ticket and coupon rules, MCT legality and regulatory eligibility should remain **deterministic rules**.

---

## 2. Domain fundamentals & terminology

| Term | Meaning | Source |
|---|---|---|
| PSS (Passenger Service System) | Core passenger suite: **reservations** (PNR), **inventory** (flight/class availability) and **DCS** (check-in, boarding, load control), usually with ticketing/e-ticket server, EMD server and schedule modules. Main vendors: Amadeus Altéa (FSC), Sabre SabreSonic → SabreMosaic, Navitaire (LCC/hybrid). Others such as IBS, Hitit and Radixx appear in analyst reports but were not individually verified here [VALIDATE] | [S-X49][S-X50][S-X11][S-X20] |
| Navitaire | LCC/hybrid PSS ("New Skies"), owned by Amadeus since **26 Jan 2016** (bought from Accenture for US$830 m). *Outdated sources still describe it as an Accenture subsidiary* | [S-X22][S-X23] |
| SabreMosaic | Sabre's offer/order platform, announced **22 May 2024**. It is organised as Offer / Order / Settle / Deliver and includes an order-based DCS and a "PSS Sync" transition module. SabreSonic remains in hybrid deployments (e.g. Virgin Australia 2024) | [S-X20][S-X21] |
| PNR | Passenger Name Record. Creation and messaging are standardised in the IATA PSC Resolutions Manual and in **AIRIMP** (A4A/IATA Reservations Interline Message Procedures) | [S-X07] |
| Mandatory PNR elements | Training sources give five: Name, Itinerary, Contact, Ticketing (ticket number or time limit), Received-from. The AIRIMP primary text was not checked, and vendor lists differ | [VALIDATE] (GDS training material only) |
| Segment status codes | HK holds confirmed · HL holds waitlist · KK carrier confirmed · KL waitlist confirmed · UC unable to confirm or waitlist · UN unable, no flight · NO no action · TK schedule change (advise passenger) · TL schedule change waitlist · HX cancel confirmed hold · WK/WL schedule change of confirmed/waitlisted segment · GK passive/guaranteed. *Travelport mapping; other systems differ* | [S-X25] |
| SSR / OSI | Special Service Request: an actionable service request, standardised codes, needs a response. Other Service Information: free-text information, no action required | [S-X07] (SSR); OSI usage seen in [S-X26] |
| Accessibility SSRs (IATA Res 700) | WCHR (can use steps; wheelchair needed for the distance to/from the aircraft) · WCHS (cannot use steps; can walk to the seat) · WCHC (completely immobile; carried to the seat) · WCOB (onboard wheelchair) · BLND · DEAF · DPNA (intellectual or developmental disability) · MAAS (meet and assist; not recognised at all EU airports) · SVAN / ESAN (service / emotional-support animal) · WCBD / WCBW / WCMP / WCLB (own wheelchair by battery type) · LEGL/LEGR/LEGB · STCR · PPOC · POXY / AOXY / OXYG · MEDA (medical clearance) | [S-X07] |
| Other common SSRs | UMNR (unaccompanied minor), PETC (pet in cabin), AVIH (animal in hold): widely documented, but not in the IATA accessibility list consulted | [VALIDATE] against AIRIMP |
| E-ticket / coupon | Flight coupons with statuses (open, checked-in/lifted, flown, exchanged…). Only the **validating carrier** can relinquish control of a coupon | [S-X01] |
| EMD-A / EMD-S | Electronic Miscellaneous Document (Res 725f/g/h). **EMD-A** (associated) is linked to an e-ticket coupon and used for paid seats or prepaid bags. **EMD-S** (standalone) is not linked to a coupon and used for change fees, deposits, residual value | [S-X01][S-X29][S-X30] |
| Marketing vs operating carrier | Res 735d roles: *original marketing carrier* (designator on the coupon; may differ under codeshare), *original operating carrier* (causes the disruption), *original receiving carrier* (onward carrier at the connection point), *new operating carrier* (carrier chosen for the reroute) | [S-X01] |
| Journey vs segment; married segments | A segment is one flight booked in a class. A journey/O&D is the passenger's origin-to-destination trip. **Married segment control** prices availability on the *connection's flow availability* and locks the segments together, so they cannot be cancelled, rebooked or priced individually | [S-X28][S-X27] |
| MCT | The shortest interval needed to transfer a passenger and their bags between flights. Defined by station standards plus carrier exceptions in SSIM Ch. 8 | [S-X02][S-X03][S-X06] |
| Involuntary reroute / INVOL | An airline-caused change of carrier, routing, class or fare type (Res 735d). Res 735e covers changes en route | [S-X01] |
| FIM (Flight Interruption Manifest) | A paper or list document that lets a passenger travel on another carrier, with billing then handled through revenue accounting. The electronic version (EFIM) is reported as **no longer supported by IATA**. The 2020 IATA IROPS guidance does not mention FIM at all | [S-X53b][S-X54] [VALIDATE current status] |
| MITA / Res 780 | Multilateral Interline Traffic Agreement. Res 780 is the framework for interlining. MITA binds parties to Res 735d for involuntary rerouting | [S-X01] |
| PNL / ADL / PTM / PSM | DCS messages: passenger name list and additions/deletions sent from reservations to DCS; passenger transfer message (onward connections); passenger service message (special needs on arrival). Only training slides were found; the definitions need checking [VALIDATE] | [S-X55] |
| PNRGOV / API | Government data push. PNR reporting follows ICAO Doc 9944 and the WCO/IATA/ICAO PNRGOV message (EDIFACT/XML). API follows WCO/IATA/ICAO guidelines (2022). Peripheral to re-accommodation, but rerouted passengers may trigger new API/PNR transmissions | [S-X32][S-X33] |
| NDC servicing / ONE Order | NDC schemas OrderReshop, OrderChange, OrderChangeNotif and OrderCancel support involuntary servicing (17.2+, enhanced 19.2). ONE Order replaces PNR, e-ticket and EMD with a single Order record; IATA targets readiness for 100 % offers and orders around 2030 | [S-X08][S-X09][S-X10] |

---

## 3. Processes, decisions & timing

### 3.1 Two different workflows: schedule change vs day-of-operations IROPS
- **[STD]** *Planned schedule change* (more than 1 day before the first impacted flight) follows RP 1735.
  - Segments move to TK/UN etc.
  - The ticket is revalidated or reissued.
  - The passenger or seller must accept or reshop [S-X01][S-X25].
- **[SPECIFIC]** Delta revalidates tickets automatically. Delta notes that about 20 % of schedule changes cannot be auto-revalidated. Agencies reissue if a ticket is not revalidated within 72 h. A new flight more than 48 h later, or an MCT that is not met, blocks revalidation [S-X26].
- **[STD]** *IROPS* means a disruption on the day of travel or the day before:
  - It triggers Res 735d involuntary reroute.
  - The carrier owes a duty of care (Res 735d Art. 6 expenses: hotel, meals, ground transport, communications).
  - Regulatory care and compensation regimes apply [S-X01][S-X34].
- **[PRACTICE]** Most schedule changes happen more than 7 days out (per Delta [S-X26]). These are batch or overnight jobs with time for passenger choice. IROPS rebooking runs in **minutes**: Air Canada reports about 10 min from cancellation notice to rebooking [S-X12].

### 3.2 IROPS passenger-impact workflow (synthesised from [S-X01][S-X11][S-X12][S-X16])
1. **Trigger:** a flight event arrives (delay estimate, cancellation, diversion, equipment swap) from OCC/MVT.
2. **Impact identification:**
   - Pull the passenger list for the flight from inventory/DCS (booked and checked-in passengers).
   - Expand each PNR to its full journey.
   - Read the **inbound and outbound connection lists**. IATA explicitly lists "look at inbound and outbound connecting passenger lists" and "determine how many passengers will need to be re-accommodated" [S-X01].
3. **Connection legality:** recompute each connection against MCT using the new estimated times. Flag connections as *broken* (under MCT or physically impossible) or *at risk* (legal but tight).
4. **Classify passengers:**
   - Terminating / connecting online / connecting interline.
   - Special needs (SSR).
   - Group, UMNR, PRM.
   - Fare/ticket constraints.
   - Loyalty tier (see 04).
5. **Generate alternatives:**
   - Own flights (direct, via other hubs, other dates).
   - Partner/interline flights where bilateral inventory agreements exist.
   - Respect cabin and class rules and protected inventory.
6. **Allocate:** run solver or rules. Vendor tools apply "recovery templates" and policies and compare scenarios with KPIs before committing [S-X11].
7. **Commit:**
   - Rebook segments (cancel unusable onward space — Res 766).
   - Reissue tickets (INVOL) and re-associate EMDs.
   - Re-seat; transfer SSRs; update DCS (PNL/ADL); re-flight bags (Res 755).
   - Update API/PNRGOV.
8. **Notify and offer choice:**
   - Default rebooking plus self-service alternatives or refund [S-X14][S-X37].
   - Vouchers.
   - Rights notices (EU261 Art. 14).
9. **Handle exceptions:** agents handle the residue that automation cannot solve (about 10 % at Air Canada [S-X12]), plus interline, groups and PRMs.
10. **Settlement (back office):** interline billing per the RAM 2-day/5-day rules and MPA proration [S-X01].

### 3.3 Hold-vs-rebook decision (connection protection)
- **[SPECIFIC]** United's **ConnectionSaver** (June 2019) automatically flags departures that could be held for late inbound connectors. It considers gate-to-gate transfer time, the ability to make up time in the air, and the impact on other passengers and flights. United reported about **14,400 connections saved in 4 months**, average hold about 6 min. Holds over 10 min go to the Network Operations Control team for approval. One analysis reports that only about 90 % of passengers held for actually board [S-X38][S-X39].
  - Before this tool, "connection planners" made these decisions manually [S-X39].
  - This hold decision is the bridge between note 02 (network) and this note (passengers).

### 3.4 Timing constraints
- **[PRACTICE]** Message latency between reservations, DCS and partners (ADL cycles, interline NI requests, ticket control exchange) limits how fast a fix can be committed. Inventory may be **taken by self-service passengers or other agents while a batch solution is computed** [VALIDATE with airline].
- **[STD]** IATA recommends PRM assistance requests at least 48 h before departure [S-X07]. Re-accommodation creates *new* flights for which the assistance provider at the new airport was not pre-alerted, so SSRs must be re-sent.

---

## 4. Data requirements & relationships

### 4.1 Entity sketch

```
Order / PNR (record locator, owner office, group flag, codeshare refs)
 ├── Passenger[n]   (name, type ADT/CHD/INF, FF number+tier, contact, API docs)
 │     ├── SSR[*]   (WCHR/UMNR/meal/PETC…, per segment, status)   ── IATA Res 700 / AIRIMP
 │     ├── Ticket[1..*] (e-ticket no., validating carrier, fare calc, endorsement)
 │     │     └── Coupon[1..4/ticket] (segment link, fare basis, bag allowance, status, control)
 │     └── EMD[*]   (EMD-A → coupon, e.g. seat/bag; EMD-S standalone)  ── Res 725f/g/h
 ├── Segment[*]     (marketing flight, operating flight, class, status HK/TK/UN…, married-group id)
 │     └── Flight-date (leg(s), STD/STA/ETD/ETA, aircraft, gate/terminal)
 │            └── Inventory (cabin/class availability, nesting, overbooking, protection; O&D/flow availability)
 ├── Remarks / OSI / queue history
 └── Journey/O&D (origin, final destination, stopovers vs connections — derived)
DCS side: Passenger-flight (check-in, seat, bag tags, boarding) + inbound/outbound connection lists (PTM)
Reference data: MCT (SSIM Ch.8), schedules (SSIM), interline/codeshare agreements, fare rules (ATPCO), regulations
```

### 4.2 Elements, origin systems and update frequency

| Element | Origin system | Update frequency / latency | Standards |
|---|---|---|---|
| PNR, passengers, segments, SSR/OSI | Reservations (host PSS; GDS for indirect sales) | Event-driven: every booking or change; high volume at peak | AIRIMP, PSCM resolutions (766, 830d for agents) [S-X01][S-X07] |
| Tickets, coupons, coupon control | E-ticket server (validating carrier); partners hold copies | On issue, exchange, check-in, lift; control passed between carriers | Res 722f/g/h [S-X01] |
| EMDs | EMD server / ancillary system | On purchase or refund; EMD-A linked to coupons | Res 725f/g/h; ATPCO optional services (RFIC/RFISC) [S-X01][S-X30] |
| Seat inventory, class availability, overbooking levels | Inventory + revenue management | Continuous (each sale); RM re-optimisation often nightly or intraday [VALIDATE] | Married-segment / O&D control vendor-specific [S-X27][S-X28] |
| Flight status (ETD/ETA, cancellations) | OCC / ops control, MVT messages, ACARS | Minutes; estimates change repeatedly | AHM movement messages (see note 02) |
| Check-in / boarding / bag status | DCS | Real time on the day; DCS opens hours before departure | PNL/ADL, PTM/PSM (Type B) [S-X55] [VALIDATE] |
| Inbound/outbound connection lists | DCS (built from PNR + check-in) | Real time on the day of departure | — |
| MCT data | IATA MCT via data aggregators (OAG, Cirium) | Periodic filings; exceptions per carrier | SSIM Ch. 8; Connection Building Filter (effective 1 Nov 2022) [S-X02][S-X04] |
| Schedules | Airline scheduling → SSIM distribution | Seasonal plus ad-hoc schedule change messages | SSIM (SSM/ASM) [VALIDATE chapter refs] |
| Fare rules / change conditions / waivers | ATPCO filings + airline waiver policy | Fares many times daily; waivers created per event | ATPCO Cat 31/33 for reissue/refund [VALIDATE] |
| Loyalty tier, CLV | Loyalty system / CRM | Daily batch typically [VALIDATE] | — |
| API / PNRGOV | DCS / reservations → governments | At check-in / defined push times | WCO/IATA/ICAO API guidelines 2022; PNRGOV EDIFACT/XML; ICAO Doc 9944 [S-X32][S-X33] |
| NDC Orders | Order management system (if any) | Event-driven; OrderChangeNotif to sellers | NDC 17.2+/19.2+; ONE Order [S-X08][S-X09] |

### 4.3 Data relationships that matter for impact assessment
- **[PRACTICE]** Impact must be computed per **journey**, not per segment. A 2-hour delay on a terminating segment is minor; the same delay on a feeder that breaks a long-haul connection may mean a next-day arrival. Bratu–Barnhart-style passenger delay calculators simulate re-accommodation to estimate real arrival delay [S-X42][S-X40].
- **[PRACTICE]** PNR ≠ party ≠ travelling group. Families may be split across PNRs, and group PNRs contain many passengers. The NDC paper notes that "today's PNR … does not support non-homogenous scenarios" [S-X08]. Keeping party integrity requires linkage heuristics [AI-OPP / VALIDATE].
- **[STD]** Codeshare means the *marketing* flight in the PNR may not be the *operating* flight in the disruption feed. Matching must use the operating flight. In codeshare, the original marketing carrier may differ from the original operating carrier [S-X01].

---

## 5. Business rules & constraints

### 5.1 IATA re-accommodation rules (Res 735d and related) — all [STD] [S-X01]
- **Resolutions in scope:**
  - 722f/g/h (e-ticket); 725/f/g/h (EMD)
  - **735d** (involuntary change); **735e** (involuntary change en route)
  - 737 (refunds); 743 (unclaimed baggage); 755 (re-flighting); 766 (interline reservations)
  - RP 1735 (planned schedule changes); RP 1790 (additional services); RP 1775 (expenses; not applied to intra-EU traffic, subject to PTC Resolution 102)
  - RAM Ch. A2 paras 2.5 and 2.7
  - Res 780 (interline framework)

  The guidance reflects the PSCM effective 1 June 2020, and US rules may differ.
- **Involuntary reroute triggers:**
  - The flight is cancelled.
  - The flight is not operated reasonably according to schedule.
  - The flight fails to stop at the passenger's destination or stopover point.
  - Confirmed space cannot be provided.
  - The carrier causes a missed connection.
- **Carrier options:** an involuntary refund (Res 737), or onward carriage "without additional charge". Onward carriage can be on the carrier's own service, on the original receiving carrier, or on "any other transportation service(s)".
- **Inventory on other carriers:**
  - The original operating carrier obtains it.
  - It uses the bilateral method if one is agreed (AIRIMP 3.18 "NI", direct access, sell-and-report, phone or email). Otherwise it must contact the new carrier first.
  - Res 766 Art. 12: the new carrier accepts the passenger if the agreed method and the agreed seat count were respected.
  - No cabin upgrade unless agreed.
- **Ticketing:** the replacement ticket must be "immediately acceptable at check-in (including self-service and online)" with the new operating carrier. This applies irrespective of fare type (award, IT/BT, bulk).
- **Baggage:** the original baggage allowance is kept (Art. 4). A prepaid bag is handled by EMD-A re-association or by putting the allowance on the reissued ticket.
- **Other ancillaries:** not rerouted to other carriers without agreement (RP 1790). They are refunded instead, and IATA recommends proactive automatic contact and refund.
- **Billing:** the 2-day/5-day rules; an INVOL designation outside 2 days is presumed to be a planned schedule change.
- **Taxes:** from 1 April 2020, taxes of the *new* routing apply (RATD).
- **Settlement:** a simplified involuntary-reroute settlement is offered via ACH with ATPCO/Accelya.

### 5.2 Connection legality
- **[STD]** Connections are bookable only at or above the applicable MCT. A carrier can *suppress* connections or file a 999-time or "Y" suppression [S-X03].
- **[PRACTICE]** Re-accommodation engines normally use the same MCT tables. Delta lists "MCT not met" on the alternative routing as a reason revalidation fails [S-X26].
- **[VALIDATE]** Whether an airline allows agents to book below MCT during IROPS (an agent override), and with what controls.

### 5.3 Inventory rules
- **[ACADEMIC/PRACTICE]** RM sets nested protection levels for higher classes and overbooking limits that offset no-shows [S-X46][S-X47]. Re-accommodated passengers normally need **seats outside the normal fare-class logic**. Engines must decide:
  - which classes they may consume (often any class in the same cabin);
  - whether to breach overbooking authorisations;
  - whether to use **married/flow** availability.

  [VALIDATE] each carrier's policy.
- **[SPECIFIC]** Amadeus Passenger Recovery explicitly balances re-accommodation against "high-yield seat sales" [S-X11]. Re-accommodation and revenue management compete for the same seats.
- **[SPECIFIC]** Example of an airline's 735d implementation: TAROM reroutes interline on the same ticket in the **lowest available booking class within the same cabin**, and applies different rules above and below a 5-hour delay [S-X56].

### 5.4 Passenger-rights constraints (hard constraints)
- **[STD]** EU 261/2004 [S-X34]:
  - Art. 8: refund, re-routing "at the earliest opportunity", or re-routing at a later date of the passenger's choice, "subject to availability of seats".
  - Art. 11: priority for PRMs, their companions and certified service dogs, and unaccompanied children; care "as soon as possible".
  - Art. 14: a written notice of rights to each affected passenger on denied boarding or cancellation, or a delay of 2 h or more; blind and visually impaired passengers get the notice by alternative means.
  - The Commission's 2024 interpretative-guidelines revision covers re-routing in good time and other carriers [S-X35]. Only the July 2024 draft annex was seen [VALIDATE final text].
  - EU261 reform proposals (2013/0072, 2023/0437) are pending [VALIDATE current status].
- **[STD]** US DOT automatic refunds (effective 28 Oct 2024) [S-X36]:
  - A refund is due if the passenger declines the alternative after a cancellation or significant change.
  - A significant change is 3+ h domestic, 6+ h international, or a change of airport.
  - Bag-fee refunds apply if a bag is delivered more than 12 h late (domestic).
  - [VALIDATE] whether the rule has been amended since 2024.
- **[PRACTICE]** Other regimes (Canada APPR, UK261, India, Brazil, etc.) are not covered here [VALIDATE] (see note 04).

### 5.5 Special-needs rules
- **[STD]** IATA Res 700 governs the acceptance and carriage of passengers with disabilities and lists the approved SSR codes [S-X07].
  - SSRs should be applied to *all flights* in the itinerary.
  - Codes must not be used to diagnose passengers.
  - MEDA is only for passengers who need medical clearance.
- **[PRACTICE]** Re-accommodation must also check the following [VALIDATE per airline]:
  - Whether the *new* carrier, aircraft or airport supports the service: wheelchair battery type (WCLB lithium is dangerous goods), stretcher, oxygen, pets, UMNR acceptance rules and minimum connection times.
  - Infants: infant-on-lap limits per aircraft (oxygen masks) and bassinets.
  - PETC/AVIH limits per flight.

---

## 6. Industry practice & real-world cases

| Case / product | Date | What it shows | Label | Source |
|---|---|---|---|---|
| **Amadeus Passenger Recovery** (Altéa) | Product page 2026 | Mass re-accommodation; recovery templates; scenario comparison with KPIs; prioritising high-value passengers; rebooking on other carriers; integration with schedule, reservations, inventory, ticketing, DCS and notifications | [SPECIFIC] | [S-X11] |
| **Air Canada** + Amadeus Passenger Recovery | Case study, c. 2024 (date inferred) | About 90 % automated; about 10 min average rebooking; 1 M+ passengers/year. Previously manual and dependent on experts | [SPECIFIC][VALIDATE] | [S-X12] |
| **SWISS** | Case study (undated) | First airline to deploy Passenger Recovery; about 150 k rebookings/year | [SPECIFIC] | [S-X13] |
| **Amadeus Self Re-accommodation** | Product page 2026 | Passenger accepts the auto-rebooked flight or picks a free alternative or refund (including vouchers), within airline rules and interline agreements; Finnair reports better satisfaction and lower contact-centre load; Air France case | [SPECIFIC] | [S-X14] |
| **Amadeus Personal Disruption Companion** (launch partner TAM/LATAM) | 2014–2015 | Early personalised mobile re-accommodation using preferences and ancillaries. **Current status unknown** | [SPECIFIC][VALIDATE] | [S-X15] |
| **Sabre IROPS Reaccommodation** | Refreshed 2019; COVID 2020 | Business-rule and customer-value prioritisation; what-if scenarios; automatic re-seating and re-association of seats, tickets and ancillaries. Version "twice as fast" (2019). 500 k+ PNRs rescheduled in March 2020 vs about 123 k in 2019 | [SPECIFIC] | [S-X16][S-X17][S-X18] |
| **Sabre Self-Service Reaccommodation** | Developer page | Automated deployment of customer waivers and self-rebooking | [SPECIFIC] | [S-X19] |
| **Navitaire** (LCC PSS) | 2016 → | No dedicated Navitaire IROPS re-accommodation product was found in public sources [VALIDATE]. The 19 Feb 2026 Navitaire outage hit check-in and boarding at IndiGo, Akasa and SpiceJet while Air India (different PSS) was largely unaffected. This shows the PSS as a single point of failure for disruption handling | [SPECIFIC] | [S-X22][S-X24] |
| **GE Aerospace Passenger Protection** | Undated | Modifies itineraries in the reservation system and displays committed results to the user and passenger | [SPECIFIC][VALIDATE] | [S-X48] |
| **United** self-service rebooking + vouchers | 22 Jun 2023 | Triggered by delays over 60 min or cancellations; app and web; nearly 50 % already self-serve | [SPECIFIC] | [S-X37] |
| **United ConnectionSaver** | 10 Jun 2019 | Automated hold-for-connection decisions; 14,4 k connections in 4 months; average hold about 6 min | [SPECIFIC] | [S-X38][S-X39] |
| **American Airlines** app self-rebooking | Date unverified | Guided self-service rebooking, bag tracking, digital vouchers; status banners incl. automatic re-accommodation | [SPECIFIC][VALIDATE date] | [S-X45] |
| **Delta** schedule-change revalidation | Policy page © 2026 | Auto-revalidation; about 20 % not revalidatable; 72 h / 48 h rules; Delta Messenger notification with an OSI marker | [SPECIFIC] | [S-X26] |
| **Heathrow / UCL** transfer-passenger connection forecasting | 2016–2021 | Machine-learning quantile forecasts of connection times, using 7 factors and 16 segments; prototype live at Heathrow; reported to beat legacy systems at identifying late passengers | [ACADEMIC→SPECIFIC] | [S-X44] |
| **Lufthansa Group NDC servicing** | 2024 report | Involuntary changes for partners not certified on NDC 24.1 are handled by LH's servicing tool; disruption and interline servicing are still gaps | [SPECIFIC] | [S-X52] |

---

## 7. AI / technology opportunities

| Opportunity | Approach | Maturity | Rules suffice? |
|---|---|---|---|
| Ticket/coupon reissue, INVOL endorsement, fare basis and bag-allowance carry-forward, RAM 2/5-day checks | Deterministic rules engine | Proven (vendor tools) | **Yes, rules only** [STD] |
| MCT legality of an itinerary | Table lookup (SSIM Ch. 8) | Proven | **Yes** |
| Eligibility (EU261/DOT refunds, care, notices) | Rules with jurisdiction logic | Proven in pieces; complex in combination | **Yes** (AI may help only to *explain* or classify cause codes) |
| **Connection-risk prediction** per passenger (P(miss) given ETA, gate/terminal distance, passenger profile, bags, PRM) | Gradient boosting / quantile regression; imbalanced classification | Research and prototype: Heathrow prototype live [S-X44]; arXiv hub model [S-X43]; interpretable models perform close to black-box ones [S-X57] | No: MCT is static; ML adds probability [AI-OPP] |
| Hold-vs-rebook decisions | Optimisation + predicted transfer times | Production at United (rules/optimisation; ML use not disclosed) [S-X38] | Hybrid |
| **Mass re-accommodation allocation** | MIP / assignment / heuristics with policy templates | Proven in production (Amadeus, Sabre) [S-X11][S-X16] | Optimisation, not ML; ML can add costs or preferences |
| Passenger choice and acceptance prediction (will they accept the default, self-serve, or call?) | Choice models, uplift models | Research, plus inferred vendor use (Amadeus PDC used preferences) [S-X15] | [AI-OPP][VALIDATE] |
| Party/group linkage across PNRs | Entity resolution (names, contacts, booking time) | Research/practice; no source found | [AI-OPP] |
| Passenger-impact scoring (expected delay minutes, misconnects, overnight risk, PRM complexity) to feed the OCC (note 02) | Simulation (Bratu–Barnhart passenger delay calculator) + ML | Academic [S-X40][S-X42] | Simulation first; ML for speed |
| Notification content (multilingual, personalised, rights text) | Templates + LLM drafting under guardrails | Emerging; no verified production case found | Templates are often enough; LLM risky for legal text [VALIDATE] |
| Agent co-pilot for residual cases (interline, PRM, groups) | LLM retrieval over policies and PSCM rules + tool calls | Emerging/unverified | [AI-OPP] — human approval needed |
| Order-based servicing (NDC/ONE Order) | Event-driven integration | Standards exist (17.2+/19.2); adoption partial | Engineering, not AI |

**[ACADEMIC] Passenger-centric metrics to optimise and report:**
- Passenger delay minutes at final destination, including re-accommodation delay [S-X40][S-X42].
- Number and percentage of disrupted passengers (cancelled or misconnected).
- Number of misconnects.
- Overnight / next-day arrivals.
- Share of passengers rebooked automatically (Air Canada 90 %) and time to rebook (about 10 min) [S-X12].
- Self-service take-up (United about 50 %) [S-X37].
- Connections saved by holds [S-X38].
- PRM/UMNR service continuity [VALIDATE metric definitions with an airline].

---

## 8. Risks, limitations, airline-model differences

- **Data quality** [PRACTICE/VALIDATE]:
  - Contact details are missing in indirect (GDS/OTA) bookings, which limits direct notification. Under NDC, sellers are notified via OrderChangeNotif instead [S-X08][S-X51].
  - SSRs are free-text or wrong (IATA warns of misuse such as WCHR for wayfinding) [S-X07].
  - Families and parties are spread across PNRs.
  - Codeshare marketing and operating flight mismatches.
  - Stale ETAs.
- **Real-time limits:**
  - Inventory changes while a solution is computed.
  - Interline seats need bilateral agreements or manual contact [S-X01].
  - Coupon control transfers and ticket reissue can fail. Delta: about 20 % of schedule changes are not auto-revalidated [S-X26].
  - The DCS view (checked-in, boarded) may lag reservations.
- **Single point of failure:** a PSS outage disables recovery tooling itself (Navitaire, Feb 2026) [S-X24].
- **Vendor claims:** automation rates and timings come from vendor case studies, are not audited and may cover only "simple" cancellations [VALIDATE].
- **Model differences:**
  - **Hub FSCs** (Air Canada, United, SWISS) have many connections. Connection risk and MCT dominate, and interline and alliance options exist.
  - **LCCs** on Navitaire are mostly point-to-point and often ticketless. IATA notes that many carriers "may not follow these Standards since they operate under a different model (e.g. Ticketless)". Interline reroute options are scarce, so re-accommodation is mostly on the carrier's own later flights or a refund [S-X01].
  - **Regional/codeshare operators** depend on the marketing carrier's PSS and rules.
- **Fairness and law:** commercial prioritisation (Amadeus "high-value passengers" [S-X11], Sabre "customer value" [S-X16]) must be subordinate to Art. 11 priorities and regulatory refunds (see note 04).
- **Outdated or conflicting information flagged:**
  1. Older sources describe Navitaire as an Accenture subsidiary. That is outdated since Jan 2016 [S-X23 vs S-X22].
  2. FIM is presented in older (2002-era) IATA material as the simple interline reroute document. The 2020 IATA IROPS guidance omits it, and EFIM is reported unsupported. Treat FIM as legacy/fallback until confirmed [S-X53b][S-X54][S-X01].
  3. WCHS wording differs between IATA ("cannot ascend/descend steps") and some secondary sources ("can walk short distances") [S-X07].
  4. IATA MCT coverage figures differ between two IATA pages (90 % of international connections vs 83 % worldwide) [S-X05].
  5. US DOT thresholds are "3+/6+ h" on DOT pages and "more than" in some press reports [S-X36].

---

## 9. Open questions / knowledge gaps / items to validate with an airline

1. The airline's PSS (Altéa / SabreSonic / Mosaic / Navitaire / other), and whether a re-accommodation module (Passenger Recovery, IROPS Reaccommodation) is licensed.
2. Which booking classes and how much over-authorisation re-accommodation may use, and how married/O&D availability is treated during IROPS.
3. The interline and codeshare partners with **bilateral IROPS inventory agreements**, and their method (NI messaging, direct access, phone).
4. Whether the airline uses MCT overrides during IROPS, and what its own MCT exceptions are at its hubs.
5. The current status of the FIM and EFIM at the airline and its partners.
6. The authoritative AIRIMP lists: mandatory PNR elements, the full SSR code set (UMNR, PETC, AVIH, INFT, etc.) and the status-code set used by the airline's host.
7. The definitions and current use of the DCS messages PNL/ADL/PTM/PSM/PFS (not verified from a primary source).
8. ATPCO categories governing involuntary reissue and refund (believed to be Cat 31/33) [VALIDATE].
9. How EMD-A re-association works in the airline's PSS, and its automatic refund process for undeliverable ancillaries.
10. Notification channels in use (SMS, email, app push, messaging) and the contact coverage of indirect bookings.
11. The current state of NDC OrderChangeNotif and ONE Order (IATA 2026 readiness report not read in full).
12. EU261 reform status, and the final text of the 2024 Interpretative Guidelines.
13. Independent evidence for the vendor automation figures, and data on failure cases.
14. Primary text of the MCT Technical Guide v2.2 (Connection Building Filter) and the current SSIM Ch. 8 (only the 2021 edition was located).
15. The exact venue of the Heathrow transfer-passenger paper (Guo, Grushka-Cockayne, De Reyck), and whether the system is still in use.

---

## 10. Sources

| ID | Tier | Title | Publisher/author | Publication date | URL | Accessed | What it supports |
|---|---|---|---|---|---|---|---|
| S-X01 | 1 | Interline Considerations on Irregular Operations (IROPs) – Guidance Document for Airlines | IATA | 25 Jun 2020 (PSCM eff. 1 Jun 2020) | https://www.iata.org/contentassets/e7a533819be440edbb1e49da96e0f2a8/guidance-document-interline-irops_25june2020.pdf | 2026-11-20 | Res 735d/735e/766/737/755/725/722, RP 1735/1790/1775, INVOL rules, RAM 2/5-day, EMD-A, NI, MITA/Res 780, connection lists |
| S-X02 | 1 | SSIM 2021 Chapter 8 – MCT Standards | IATA | 2021 | https://www.iata.org/contentassets/638f0938b3dd451b872a1d8357755421/ssim2021_chapter-8-mctstandards.pdf | 2026-11-20 | MCT standard, MCTG governance (search excerpt) |
| S-X03 | 1 | Minimum Connecting Time User Guide v1.1 | IATA MCTG | Rev. Feb 2020 | https://www.iata.org/contentassets/638f0938b3dd451b872a1d8357755421/minimum-connecting-time-user-guide_version-1.1.pdf | 2026-11-20 | MCT data elements (2018), DD/DI/ID/II, exceptions, suppressions, codeshare, OAG/Cirium aggregators |
| S-X04 | 1 | MCT Technical Guide v2.2 | IATA | n.d. | https://www.iata.org/contentassets/638f0938b3dd451b872a1d8357755421/minimum-connecting-time-technical-guide_version-2.2.pdf | 2026-11-20 | Connection Building Filter eff. 1 Nov 2022 (search excerpt only) |
| S-X05 | 1 | Station Standard MCT / MCT Basic product pages | IATA | 2026 edition | https://www.iata.org/en/publications/manuals/station-standard-minimum-connecting-time-mct/ | 2026-11-20 | 400+ airports; coverage-figure conflict |
| S-X06 | 2 | Minimum Connection Times: An Insider's Guide | OAG | n.d. | https://www.oag.com/minimum-connection-time | 2026-11-20 | MCT approval process via airport committees |
| S-X07 | 1 | Best Practices on the Application of SSR Codes and Assistance Service | IATA | 21 Aug 2024 (PDF metadata) | https://www.iata.org/contentassets/7b3762815ac44a10b83ccf5560c1b308/best-practices-on-the-application-of-ssr-codes-and-assistance-service.pdf | 2026-11-20 | Res 700 SSR codes and definitions, AIRIMP/PSCM, 48 h recommendation |
| S-X08 | 1 | NDC In Focus: Servicing in NDC | IATA | Jun 2019 | https://www.iata.org/contentassets/6de4dce5f38b45ce82b0db42acd23d1c/ndc-infocus-servicing.pdf | 2026-11-20 | Involuntary servicing, OrderChangeNotif, 17.2/19.2, PNR split constraint |
| S-X09 | 1 | Fact sheet – ONE Order | IATA | Dec 2025 | https://www.iata.org/en/iata-repository/pressroom/fact-sheets/fact-sheet-one-order/ | 2026-11-20 | ONE Order role, airline-specific timelines (search excerpt) |
| S-X10 | 1 | Readiness and roadmap to 100% Offers & Orders 2026 | IATA | 2026 | https://www.iata.org/globalassets/iata/programs/airline-retailing-section/iata-readiness-and-roadmap-to-100-offers-orders-2026.pdf | 2026-11-20 | 2030 readiness goal, surveys (excerpt only; not read in full) |
| S-X11 | 2 | Amadeus Passenger Recovery | Amadeus | Live page 2026 | https://amadeus.com/en/portfolio/airlines/passenger-recovery | 2026-11-20 | Product capabilities, Altéa integration, high-value prioritisation |
| S-X12 | 2 | Managing disruption with control, credibility and care at Air Canada | Amadeus | c. 2024 (inferred) | https://amadeus.com/en/resources/case-study/managing-disruption-with-control-credibility-and-care-at-air-canada | 2026-11-20 | 90 % automation, 10 min, 1 M+ pax/yr |
| S-X13 | 2 | SWISS disruption management case study | Amadeus | n.d. | https://amadeus.com/en/resources/case-study/swiss-disruption-management | 2026-11-20 | First deployer, 150 k rebookings/yr (search excerpt) |
| S-X14 | 2 | Amadeus Self Re-accommodation | Amadeus | Live page 2026 | https://amadeus.com/en/portfolio/airlines/amadeus-self-re-accommodation | 2026-11-20 | Self-service capabilities; Finnair, Air France |
| S-X15 | 2 | Industry-first solution helps airlines better manage delayed/cancelled flights (Personal Disruption Companion) | Amadeus (+ trade press) | Dec 2014 / Jan 2015 | https://amadeus.com/en/blog/articles/industry-first-solution-helps-airlines-better-manage-delayed-cancelled-flights | 2026-11-20 | TAM launch, preference/ancillary-based re-accommodation |
| S-X16 | 2 | IROPS Reaccommodation (marketplace listing) | Sabre via SoftwareOne | n.d. | https://platform.softwareone.com/product/irops-reaccommodation/PCP-5136-0688 | 2026-11-20 | Capabilities, value prioritisation, ancillary re-association |
| S-X17 | 2 | Customer story – IROPS reaccommodate passengers | Sabre | 2020 | https://your.sabre.com/inthistogether/customer_story_irops_reaccommodate_passengers | 2026-11-20 | 500 k+ PNRs in Mar 2020 vs about 123 k in 2019 |
| S-X18 | 4 | Sabre rolls out airline platform updates | TTG Asia | 27 Jun 2019 | https://www.ttgasia.com/2019/06/27/sabre-rolls-out-airline-platform-updates-teases-intelligent-retail-solution-for-hotels/ | 2026-11-20 | 2019 refresh, "twice as fast" |
| S-X19 | 2 | Self Service Reaccommodation feature | Sabre Dev Studio | n.d. | https://developer.sabre.com/self-service-reaccommodation | 2026-11-20 | Waivers and self-service rebooking |
| S-X20 | 2 | Sabre introduces SabreMosaic | Sabre / PR Newswire | 22 May 2024 | https://prnewswire.com/news-releases/sabre-introduces-sabremosaic-its-revolutionary-offer-and-order-retailing-platform-for-airlines-302153126.html | 2026-11-20 | Offer/order platform, domains, order-based DCS |
| S-X21 | 1 | IT vendor modularity in action (joint presentation) | IATA (event deck) | 2025 | https://www.iata.org/contentassets/06c4cf2ba09649008de86be7898af8fa/presentations-2025/it-vendor-modularity-in-action_joint-presentation.pdf | 2026-11-20 | PSS Sync as transitional module (excerpt) |
| S-X22 | 2 | Accenture completes sale of Navitaire to Amadeus | Accenture newsroom (+ Amadeus release) | 26 Jan 2016 | https://newsroom.accenture.com/news/2016/accenture-completes-sale-of-navitaire-to-amadeus | 2026-11-20 | Navitaire ownership, US$830 m |
| S-X23 | 3 | Another Navitaire-maintained reservation system has troubles | IEEE Spectrum | c. 2010 | https://spectrum.ieee.org/riskfactor/aerospace/aviation/another-navitairemaintained-reservation-system-has-troubled | 2026-11-20 | Outdated ownership claim (flag) |
| S-X24 | 4 | Navitaire outage – check-in delays Delhi/Mumbai | AirHelp | Feb 2026 | https://www.airhelp.com/en/flight-disruptions/navitaire-outage-check-in-delays-delhi-mumbai-20022026/ | 2026-11-20 | 19 Feb 2026 outage, affected LCCs |
| S-X25 | 2 | PNR Status Codes | Travelport uAPI help | n.d. | https://support.travelport.com/webhelp/uAPI/Content/Air/Shared_Air_Topics/PNR_Status_Codes.htm | 2026-11-20 | Segment status codes |
| S-X26 | 1 | Schedule Change and Ticket Revalidation – General Overview | Delta Air Lines (agency policy) | © 2026 (no update date) | https://pro.delta.com/content/agency/hk/zt/policy-library/schedule-change-and-irregular-operations/schedule-change-and-ticket-revalidation-policy.html | 2026-11-20 | Revalidation, 20 %, 72 h/48 h, MCT, Delta Messenger, OSI |
| S-X27 | 1 | Rules and Penalties for Married Segment Control (MSC) | Thai Airways | n.d. | https://www.thaiairways.com/content/dam/thaiairways/pdf/travelagent/Rules-and-Penalties-for-Married-Segment-Control-MSC.pdf | 2026-11-20 | Married segments cannot be handled individually (excerpt) |
| S-X28 | 4 | Married segment (glossary) | AltexSoft | n.d. | https://www.altexsoft.com/glossary/married-segment/ | 2026-11-20 | Flow vs local availability mechanism |
| S-X29 | 1 | Electronic Miscellaneous Document – EMDs | American Airlines SalesLink | n.d. | https://saleslink.aa.com/en-US/resources/html/electronic-miscellaneous-document.html | 2026-11-20 | EMD-A linked to PNR/Order |
| S-X30 | 1 | EMD | Finnair (easy.finnair.com) | n.d. | https://easy.finnair.com/en/reservation---ticketing/ticketing/emd | 2026-11-20 | EMD-S has no RES/DCS interaction; EMD-A needs a confirmed SSR |
| S-X31 | 4 | Electronic miscellaneous document | Wikipedia | n.d. | https://en.wikipedia.org/wiki/Electronic_miscellaneous_document | 2026-11-20 | Res 725F/G/H (cross-checked with S-X01) |
| S-X32 | 1 | API Guidelines and PNR Reporting Standards | ICAO / WCO / IATA | 2022 guidelines | https://www.icao.int/facilitation-programmes/api-guidelines-and-pnr-reporting-standards | 2026-11-20 | API/PNR governance, Doc 9944, push method |
| S-X33 | 1 | PNRGOV EDIFACT Implementation Guide 21.1 | IATA/WCO/ICAO | 2021 | https://www.iata.org/contentassets/18a5fdb2dc144d619a8c10dc1472ae80/pnrgov-edifact-implementation-guide_21_1.pdf | 2026-11-20 | PNRGOV message existence/version |
| S-X34 | 1 | Regulation (EC) No 261/2004, Arts 8, 11, 14 | EU (UK-retained text on legislation.gov.uk; wording of these articles matches the EU original) | 2004 | https://www.legislation.gov.uk/eur/2004/261/article/14/data.htm | 2026-11-20 | Re-routing, PRM/UMNR priority, written notice |
| S-X35 | 1 | C(2024) 5056 final – Annex, draft Commission Notice on Interpretative Guidelines | European Commission | 22 Jul 2024 | https://transition-pathways.europa.eu/system/files/2024-09/C_2024_5056_1_EN_annexe_acte_autonome_cp_part1_v3%20%281%29.pdf | 2026-11-20 | Re-routing guidance (draft; final not checked) |
| S-X36 | 1 | What airline passengers need to know about DOT's automatic refund rule | US DOT | 2024 | https://www.transportation.gov/briefing-room/what-airline-passengers-need-know-about-dots-automatic-refund-rule | 2026-11-20 | 3+/6+ h, effective 28 Oct 2024 |
| S-X37 | 1 | United's new app feature helps customers re-book and receive meal and hotel vouchers automatically | United Airlines | 22 Jun 2023 | https://united.mediaroom.com/2023-06-22-Uniteds-New-App-Feature-Helps-Customers-Re-book-and-Receive-Meal-and-Hotel-Vouchers-Automatically | 2026-11-20 | Self-service rebooking, about 50 % self-serve |
| S-X38 | 1 | United Airlines makes connecting the world easier than ever with ConnectionSaver | United Airlines | 10 Jun 2019 | https://united.mediaroom.com/2019-06-10-United-Airlines-Makes-Connecting-the-World-Easier-Than-Ever-with-ConnectionSaver | 2026-11-20 | Automated holds, 14,400 connections |
| S-X39 | 4 | A more detailed look at United's ConnectionSaver | Cranky Flier (B. Snyder) | 20 Jun 2019 | https://crankyflier.com/2019/06/20/a-more-detailed-look-at-uniteds-connectionsaver/ | 2026-11-20 | Manual connection planners; about 90 % of held passengers board |
| S-X40 | 3 | Modeling Passenger Travel and Delays in the National Air Transportation System | Barnhart, Fearing, Vaze — Operations Research 62(3):580–601 | 2014 | https://dspace.mit.edu/handle/1721.1/89059 | 2026-11-20 | Passenger delay modelling; about 50 % from disruptions |
| S-X41 | 3 | NEXTOR research symposium slides (Barnhart) | NEXTOR / MIT | 2015 | https://nextor.umd.edu/files/2019/02/2015_NRS_Barnhart-2dwakqp.pdf | 2026-11-20 | 52/29/19 % breakdown (excerpt) |
| S-X42 | 3 | Bratu & Barnhart, passenger delay calculator / passenger-centric metrics | NEXTOR / MIT | 2001 (AAC) and later | https://nextor.umd.edu/files/2019/02/2001_AAC_Barnhart-Bratu-1hnpw1l.pdf | 2026-11-20 | Flight metrics understate passenger delay; passenger-centric metrics |
| S-X43 | 3 | Decision Support Models for Predicting and Explaining Airport Passenger Connectivity from Data | arXiv 2111.01915 | 2021 | https://arxiv.org/pdf/2111.01915 | 2026-11-20 | ML missed-connection prediction at a hub |
| S-X44 | 3 | Forecasting airport transfer passenger flow using real-time data and machine learning (Guo, Grushka-Cockayne, De Reyck) | HBS Working Knowledge abstract / UCL | c. 2020–2021 | https://hbswk.hbs.edu/item/forecasting-airport-transfer-passenger-flow-using-real-time-data-and-machine-learning | 2026-11-20 | Heathrow prototype; quantile forecasts; 7 factors/16 segments |
| S-X45 | 4 | American app update adds self-rebooking during disruptions | AltexSoft news | date unverified | https://www.altexsoft.com/travel-industry-news/american-app-update-adds-self-rebooking-during-disruptions/ | 2026-11-20 | AA self-service flow |
| S-X46 | 3 | Transportation Systems Analysis, Lecture 17 (RM, EMSRb) | MIT OpenCourseWare | 2008 | https://live.ocw.mit.edu/courses/1-201j-transportation-systems-analysis-demand-and-economics-fall-2008/0fc64f08e8343d2c4b0f2c27bc13690d_MIT1_201JF08_lec17.pdf | 2026-11-20 | Nested protection levels |
| S-X47 | 1 | Overbooking (position paper) | IATA | n.d. | https://www.iata.org/contentassets/2e46aace261040b9a47fb7b9da18efc9/overbooking.pdf | 2026-11-20 | Rationale for overbooking |
| S-X48 | 2 | Network Operations – Passenger | GE Aerospace | n.d. | https://www.geaerospace.com/sites/default/files/networkoperations_passenger.pdf | 2026-11-20 | Passenger Protection product (excerpt) |
| S-X49 | 4 | Passenger Service System (glossary) | AltexSoft | n.d. | https://altexsoft.com/glossary/passenger-service-system-pss | 2026-11-20 | Top-3 PSS about 60 % share (undated; weak) |
| S-X50 | 2 | The Market for Airline Passenger Services Systems (2016 contents; 2020 summary) | T2RL | 2016 / 2020 | https://www.t2rl.net/docs/The_Market_for_Airline_Passenger_Services_Systems_2020-SUMMARY.pdf | 2026-11-20 | Amadeus+Navitaire about 37 % (2016); vendor landscape |
| S-X51 | 1 | OrderChangeNotif documentation | Virgin Atlantic NDC | n.d. | https://ndc.virginatlantic.com/docs/OrderChangeNotif | 2026-11-20 | IROPS/schedule change via OrderChangeNotifRQ (excerpt) |
| S-X52 | 4 | NDC: when things go wrong | Business Travel Executive | c. 2024 | https://www.businesstravelexecutive.com/special-report/ndc-when-things-go-wrong/ | 2026-11-20 | LH Group servicing gaps (excerpt) |
| S-X53b | 4 | Airline Guide to Involuntary Rerouting, 1st ed. (unofficial copy) | IATA (via Scribd) | 2002 | https://www.scribd.com/document/583107345/Inv-Rerouting-1st-Ed-2002 | 2026-11-20 | Historical FIM section (outdated, unofficial) |
| S-X54 | 4 | EFIM Electronic Flight Interruption Manifest (No longer supported by IATA) | KIU wiki | n.d. | https://kiu.atlassian.net/wiki/spaces/KOD/pages/4146070 | 2026-11-20 | EFIM unsupported |
| S-X55 | 4 | SITA telegrams training slides (PTM/PSM/PAL/CAL) and AeroCRS PNL/ADL article | Scribd upload / AeroCRS | n.d. / 2016 | https://support.aerocrs.com/hc/en-us/articles/210799203-05-JUN-2016-New-PNL-ADL-management-screen | 2026-11-20 | DCS message meanings (weak; validate) |
| S-X56 | 1 | Neregularități zbor (flight irregularities) | TAROM | n.d. | https://www.tarom.ro/de/informatii-interne-tarom/neregularitati-zbor | 2026-11-20 | Airline 735d practice: lowest class in the same cabin; 5 h distinction (excerpt) |
| S-X57 | 3 | Interpretable models for hub connection prediction (MSc thesis 86637) | Instituto Superior Técnico, Lisbon | c. 2021 | https://fenix.tecnico.ulisboa.pt/downloadFile/563345090420541/Thesis_86637.pdf | 2026-11-20 | Interpretable models perform close to black-box ones (excerpt) |

*Notes on evidence:* S-X01, S-X03, S-X07 and S-X08 were read in full text. Most other entries were checked through the vendor or airline page or a search excerpt only, as marked. All vendor performance numbers are self-reported.
