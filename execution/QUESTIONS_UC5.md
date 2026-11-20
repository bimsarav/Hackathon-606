# UC5 Flight & Passenger Disruption Management: clarification register
Requirement: input/requirements/Disruption_Management_UC5.docx + input/requirements/UC5_briefing_transcript.txt + PO Q&A input/requirements/UC5_QnA_2026-11-20.txt.
Product owner: Shaharsad Salam (Sheru). Clarifications are asked on our behalf by Bimsara Vikum Bandara. Data: input/data/disruption-uc5/ (git-ignored, treated as real passenger data).
Status: questions closed 2026-11-20. Data Q4–Q11 → synthetic data plus assumptions (input/data/disruption-uc5/synthetic/README.md). Rules Q12–Q15 → agent proposals (same README). Q26 → key in input/secrets/AI_API_KEY. **Solution build needs the user's explicit approval.**

| # | Question (short) | Answer 2026-11-20 |
|---|---|---|
| 1 | Product via full workflow, deadline, demo on OCI server | Not applicable |
| 2 | Demo "now" / 7-day window start | Default: settable simulated clock, starting 2026-11-20 |
| 3 | Real or synthetic data; show in demo; store on cloud; send to external AI | Synthetic, but treat it as real data. Yes / yes / yes |
| 4 | Loyalty tier, member ID, travel frequency source | OPEN |
| 5 | Special-assistance (SSR) source, infant-to-adult link | OPEN |
| 6 | Row grain, fare per pax/leg, currency, TNFSEG/MODSEG/CNXSEG, OHD bookings | OPEN |
| 7 | Zero-fare rows, non-rev (PC/CS?), booking class → fare family | OPEN |
| 8 | Journey building via SHJ connections | Yes; connection window 15 min to 20 h. Booking-class → fare-family list: OPEN |
| 9 | Time zones | UTC. The schedule's 05:00 is UTC and the inventory's 09:00 is local, so map the two. Flight numbers with prefix 02 are buses (bus + air) |
| 10 | CURTAIL / OVERSELL; inventory capture date | CURTAIL lowers the flight's sellable limit (e.g. 170 → 160); OVERSELL raises it. Capture date: OPEN |
| 11 | Delay code scheme | OPEN |
| 12 | Priority order and passenger-rights regimes | OPEN |
| 13 | Allowed recovery levers, crew | PO (Q&A): aircraft swap, equipment change, delay and cancellation are all valid. Build two levers first, add a third only if time allows. Which two, and crew: OPEN |
| 14 | Rebooking scope (own/group/other carriers, next day) | OPEN |
| 15 | Cost figures | OPEN |
| 16 | Disruption definition | Default: ≥15 min, ≥60 min, cancellation |
| 17 | Message language and channel | English only |
| 18 | Stack | Agent chooses (autonomous selection authorised) |
| 19 | Demo roles | Default: OCC and PCU demo roles |
| 20 | Demo scenarios | Both: (a) inbound SHJ flight delayed 120–180 min (rotation knock-on + misconnects); (b) cancellation with insufficient seats on alternatives (priority decides) |
| 21 | Agent authority | Recommend only (human approves) |
| 22 | Airport time zones | Use a public time-zone dataset |
| 23 | Bus legs (02 prefix) as connections / rebooking alternative | PO: flights only for now; buses later [interpretation, confirm] |
| 24 | Other airlines in rotation file (3L, 9P, 3O, E5, 4P) | Include them where we have data |
| 25 | Registration → aircraft type/seat list | PO: take seat counts from the inventory allocation, including curtail and oversell. A registration → aircraft model file may be uploaded later (pending) |
| 26 | Claude API key delivery; template fallback without key | OPEN (proposed: git-ignored .env; template fallback) |
| 27 | Booking vs inventory mismatch | PO: expected (bookings lag inventory, sales run in parallel). The process must not break on a mismatch. Synthetic bookings may be added, or bookings marked cancelled, to fill gaps |
| 27 | First two recovery levers | Agent's suggestion: delay + aircraft swap (scenario a). Scenario b is a cancellation event with passenger re-accommodation |
| 28 | Swap vs equipment change | Aircraft swap only (same type). Equipment change is a later phase |
| 29 | Source of truth on mismatch | Yes: inventory = capacity, bookings = who is booked; flag mismatches and continue; label all synthetic or adjusted records |
| 30 | Registration → aircraft file | Create a synthetic file now from the given data and domain knowledge; replace it when the real file arrives |
| 4–11 | Open data questions | User: create synthetic data from knowledge plus the given data → done (see synthetic/README.md) |
| 12–15 | Open rule questions | User: agent's suggestion → recorded in synthetic/README.md "Rule defaults" |
| 26 | AI API key | Supplied as a file; moved to input/secrets/AI_API_KEY (git-ignored, 600). Template fallback when absent |
