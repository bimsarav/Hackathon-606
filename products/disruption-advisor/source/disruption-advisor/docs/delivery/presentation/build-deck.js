// aeroRecovery hackathon deck: slides 1-9 = UC5 acceptance criteria, slides 10-13 = extra features.
// Screenshots: production via Chrome, 21 Nov 2026. UI http://92.5.154.198:8080, API http://92.5.154.198:8888.
const pptxgen = require("pptxgenjs");
const path = require("path");
const sz = require("image-size");
const imageSize = sz.imageSize || sz.default || sz;
const { applyTheme } = require(process.env.APPLY_THEME);

const D = __dirname;
const SH = (n) => path.join(D, "shots", n + ".png");
const OUT = process.env.OUT || path.join(D, "aeroRecovery-deck.pptx");

const THEME = {
  name: "aeroRecovery",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B2233", lt1: "FFFFFF", dk2: "0B1230", lt2: "F1F4F9",
    accent1: "1455B5", accent2: "E3173E", accent3: "1E8E5A", accent4: "C77C00",
    accent5: "5B6B85", accent6: "38C6E8", hlink: "1455B5", folHlink: "5B6B85",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.title = "aeroRecovery: Disruption Advisor (UC5)";
pres.subject = "ISA Hackathon 606, UC5 Intelligent Flight and Passenger Disruption Management";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

// ---------- layouts ----------
pres.defineSlideMaster({
  title: "Title dark",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 2.2, w: 6.2, h: 1.0, fontSize: 48, bold: true, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 3.3, w: 6.0, h: 1.2, fontSize: 20, color: "C9D3E8", valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
});
const contentMaster = (title, dark) => pres.defineSlideMaster({
  title,
  background: { color: dark ? C.text2 : C.background1 },
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: 0.6, y: 0.35, w: 10, h: 0.3, fontSize: 12, bold: true, color: dark ? C.accent6 : C.accent1, charSpacing: 1, align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.65, w: 12.1, h: 0.7, fontSize: 30, bold: true, color: dark ? C.background1 : C.text2, valign: "top", align: "left", margin: 0 }, text: "" } },
    { text: { text: "aeroRecovery · UC5 · ISA Hackathon 606", options: { x: 0.6, y: 7.08, w: 6, h: 0.22, fontSize: 10, color: dark ? "8C9AB8" : C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: 12.3, y: 7.08, w: 0.45, h: 0.22, fontSize: 10, color: dark ? "8C9AB8" : C.accent5, align: "right" },
});
contentMaster("Content", false);
contentMaster("Content dark", true);

// ---------- helpers ----------
const T = (s, text, o) => s.addText(text, Object.assign({ isTextBox: true, margin: 0, fontSize: 14, color: C.text1, valign: "top" }, o));

// Place a screenshot inside box (x, y, maxW, maxH), keeping its aspect; align "left"|"center"|"right"
function shot(s, name, x, y, maxW, maxH, opts = {}) {
  const { width: pw, height: ph } = imageSize(SH(name));
  let w = maxW, h = (w * ph) / pw;
  if (h > maxH) { h = maxH; w = (h * pw) / ph; }
  if (opts.align === "center") x += (maxW - w) / 2;
  if (opts.align === "right") x += maxW - w;
  const pad = 0.04;
  s.addShape(pres.shapes.RECTANGLE, {
    objectName: "Frame " + name, x: x - pad, y: y - pad, w: w + 2 * pad, h: h + 2 * pad,
    fill: { color: C.background1 }, line: { color: "D5DCE8", width: 0.75 },
    shadow: { type: "outer", color: "0B1230", opacity: 0.16, blur: 7, offset: 2, angle: 90 },
  });
  s.addImage({ path: SH(name), x, y, w, h, altText: opts.alt || name, objectName: "Screenshot " + name });
  return { x, y, w, h, b: y + h, r: x + w };
}

function stat(s, x, y, w, big, label, color, bigSize = 30) {
  T(s, big, { x, y, w, h: 0.55, fontSize: bigSize, bold: true, color: color || C.accent1, objectName: "Stat " + label.slice(0, 24) });
  T(s, label, { x, y: y + 0.56, w, h: 0.5, fontSize: 12, color: C.accent5 });
}

function card(s, x, y, w, h, head, body, opts = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    objectName: "Card " + head, x, y, w, h, rectRadius: 0.08,
    fill: { color: opts.fill || C.background2 }, line: { color: opts.fill || C.background2, width: 0 },
  });
  T(s, head, { x: x + 0.2, y: y + 0.15, w: w - 0.4, h: 0.32, fontSize: opts.headSize || 15, bold: true, color: opts.headColor || C.text2 });
  if (body) T(s, body, { x: x + 0.2, y: y + 0.5, w: w - 0.4, h: h - 0.6, fontSize: opts.bodySize || 13, color: opts.bodyColor || C.text1 });
}

function bullets(s, items, o) {
  s.addText(items.map((t, i) => {
    const runs = Array.isArray(t) ? t : [{ text: t }];
    return runs.map((r, j) => ({ text: r.text, options: Object.assign({}, r.options || {}, (runs.length === 1 ? { bullet: { indent: 14 } } : {}), j === runs.length - 1 && i < items.length - 1 ? { breakLine: true } : {}) }));
  }).flat(), Object.assign({ isTextBox: true, margin: 0, fontSize: 13, color: C.text1, valign: "top", paraSpaceAfter: 5 }, o));
}
const B = (t) => ({ text: t, options: { bold: true } });

// UC5 criterion checklist: [ [label, done], ... ]
function criteria(s, x, y, w, items, title) {
  T(s, title || "UC5 acceptance criteria", { x, y, w, h: 0.3, fontSize: 13, bold: true, color: C.accent1 });
  s.addText(items.map((t, i) => [
    { text: "✓  ", options: { bold: true, color: C.accent3 } },
    { text: t, options: i < items.length - 1 ? { breakLine: true } : {} },
  ]).flat(), { isTextBox: true, x, y: y + 0.34, w, h: 0.24 * items.length + 0.1, margin: 0, fontSize: 12, color: C.text1, valign: "top", paraSpaceAfter: 4 });
  return y + 0.34 + 0.24 * items.length + 0.35;
}

const content = (section, kicker, title, dark) => {
  const s = pres.addSlide({ masterName: dark ? "Content dark" : "Content", sectionTitle: section });
  s.addText(kicker, { placeholder: "kicker" });
  s.addText(title, { placeholder: "title" });
  return s;
};

// =================== UC5 (slides 1-9) ===================
pres.addSection({ title: "UC5 acceptance criteria" });
const SEC1 = "UC5 acceptance criteria";

// 1. Title
{
  const s = pres.addSlide({ masterName: "Title dark", sectionTitle: SEC1 });
  s.addImage({ path: path.join(D, "badge.png"), x: 0.7, y: 1.2, w: 0.8, h: 0.8, altText: "aeroRecovery badge", objectName: "Badge" });
  s.addText("aeroRecovery", { placeholder: "title" });
  s.addText("AI disruption advisor for OCC and the Passenger Control Unit", { placeholder: "body" });
  T(s, "Turns a flight disruption into an explained, approved recovery plan before its impact cascades across the network.", { x: 0.7, y: 4.45, w: 5.9, h: 0.9, fontSize: 16, italic: true, color: HEX.accent6 });
  T(s, [
    { text: "ISA Hackathon 606 · UC5 Flight & Passenger Disruption Management", options: { breakLine: true } },
    { text: "Live on the provided VM: UI http://92.5.154.198:8080 · API :8888", options: { bold: true, color: C.background1 } },
  ], { x: 0.7, y: 6.1, w: 6.3, h: 0.7, fontSize: 13, color: "8C9AB8" });
  shot(s, "d-top", 7.2, 1.6, 5.55, 3.2, { alt: "Delay analysis for G9519 with recommendation, KPIs and three strategies" });
  T(s, "Production: G9519 DAC→SHJ 195 min late, real schedule and bookings", { x: 7.2, y: 3.85, w: 5.55, h: 0.3, fontSize: 11, color: "8C9AB8" });
  s.addNotes("aeroRecovery answers the UC5 question: how can AI predict, assess and minimise the impact of flight disruptions on the network and on passengers while prioritising passenger recovery intelligently. Every screenshot in this deck was captured from the production deployment on the provided VM on 21 Nov 2026, using the supplied 2026 G9 data.");
}

// 2. Coverage matrix
{
  const s = content(SEC1, "UC5 COVERAGE", "Every UC5 challenge is covered in one workflow");
  const hdr = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 }, fontSize: 12 } });
  const rows = [
    [hdr("UC5 requirement"), hdr("How aeroRecovery meets it"), hdr("Slide")],
    ["Challenge 1 · Predictive disruption intelligence", "7-day cascade along aircraft rotations, inbound-delay impact, misconnection risk per passenger; ML watchlist", "4 · 12"],
    ["Challenge 2 · Intelligent flight recovery", "Absorb, swap, hold a connection, cancel or consolidate a round trip; costed trade-offs; 3 strategies", "5"],
    ["Challenge 3 · Passenger recovery", "Misconnect list with slack and alternatives, optimal rebooking within real seats, families kept together, messages", "6"],
    ["AI-driven passenger prioritisation", "Mandatory tiers + configurable weighted score, points per attribute, what-if weights, insufficient-seat plan", "7"],
    ["Challenge 4 · Decision support", "One consolidated view, scenario comparison, AI explanation, simulate before acting, approve / override / audit", "8"],
    ["Example scenario (§6)", "Hub-bound delay with tight turn and onward connections, answered with live numbers", "3"],
    ["Deliverables (§8)", "Working prototype on the VM, live demo, weighted prioritisation, AI techniques, benefits", "9"],
  ].map((r, i) => i === 0 ? r : r.map((c, j) => ({ text: c, options: { fontSize: 12, bold: j === 0, color: j === 2 ? HEX.accent1 : HEX.dk1, align: j === 2 ? "center" : "left", fill: { color: i % 2 ? HEX.lt1 : HEX.lt2 } } })));
  s.addTable(rows, { x: 0.6, y: 1.65, w: 12.13, colW: [3.6, 7.73, 0.8], rowH: 0.5, border: { type: "solid", pt: 0.5, color: "D5DCE8" }, valign: "middle", margin: [0.04, 0.1, 0.04, 0.1] });
  T(s, [B("Beyond UC5 (slides 10–13): "), { text: "crew FDP alerts · passenger goodwill rewards · 7-day delay prediction · evaluator mode with your own test data" }], { x: 0.6, y: 6.05, w: 12.13, h: 0.6, fontSize: 14, color: C.text2 });
  s.addNotes("This slide is the traceability view for the judges: each UC5 challenge and expected-solution item, how it is met, and where it is shown. Slides 10 to 13 cover the features built beyond the UC5 brief.");
}

// 3. Example scenario answered
{
  const s = content(SEC1, "UC5 EXAMPLE SCENARIO (§6), ANSWERED WITH LIVE DATA", "A hub-bound delay with a tight turn and connections");
  const r = shot(s, "d-top", 0.6, 1.65, 6.6, 4.3, { alt: "G9519 recommendation, KPIs and the three strategies compared" });
  T(s, "G9519 DAC→SHJ, 168 booked, 195 min late, aircraft due out again 55 min after arrival", { x: 0.6, y: r.b + 0.12, w: 6.6, h: 0.3, fontSize: 11, color: C.accent5 });
  const qa = [
    ["Impacted flights and 7-day cascade?", "47 flights touched over 7 days; recommended option delays 3, absorbing the delay delays 5"],
    ["Who misses connections, what alternatives?", "286 connections checked, 100 broken; 98 rebooked within 24 h, 2 get hotel or refund"],
    ["How to prioritise with limited seats?", "Care and urgency tiers first, then a weighted score; CP-SAT fills real seats"],
    ["Can AI explain its reasoning?", "Yes: points per attribute, cost breakdown, and Claude's wording of engine facts"],
    ["Which strategy balances best?", "Lowest cost: swap A6-ANO, AED 127k, saving AED 292k vs worst; Protect passengers: swap A6-ARI, 83 missed"],
    ["How does AI support teams?", "Approve, override with reason, audit trail, passenger message drafts"],
  ];
  let y = 1.6;
  qa.forEach(([q, a]) => {
    T(s, q, { x: 7.55, y, w: 5.2, h: 0.28, fontSize: 13, bold: true, color: C.text2 });
    T(s, a, { x: 7.55, y: y + 0.29, w: 5.2, h: 0.5, fontSize: 12 });
    y += 0.86;
  });
  s.addNotes("These are the UC5 §6 questions, answered from the live system for a real flight. The example in the brief is a 120-minute delay; we show 195 minutes because it also triggers the crew alert covered on slide 10. All counts and costs come from the recovery engine.");
}

// 4. Challenge 1
{
  const s = content(SEC1, "CHALLENGE 1 · PREDICTIVE DISRUPTION INTELLIGENCE", "See the cascade along the rotation before it happens");
  const a = shot(s, "d-rotation", 0.6, 1.65, 7.6, 3.0, { alt: "Rotation board before and after the swap for A6-ARD and A6-ANO" });
  shot(s, "d-flights", 0.6, a.b + 0.25, 7.6, 6.75 - a.b - 0.25, { alt: "Flights affected over the next 7 days with new times and delays" });
  const cb = criteria(s, 8.6, 1.6, 4.15, [
    "Trends from 2026 history (delay codes, turns)",
    "Flights vulnerable through aircraft rotations",
    "Inbound delay impact on subsequent flights",
    "Passenger misconnections vs MCT",
    "Network consequences over the next 7 days",
  ]);
  bullets(s, [
    [B("Minimum turns measured "), { text: "from 2026 actuals: 51 min at SHJ, 36 min outstations" }],
    [B("Backtested "), { text: "on 1,634 real delays: mean error 25 min vs 57 min without knock-on" }],
    [B("ML 7-day watchlist "), { text: "ranks flights before the day (slide 12)" }],
  ], { x: 8.6, y: cb, w: 4.15, h: 6.75 - cb, fontSize: 13 });
  s.addNotes("The rotation board shows the late aircraft A6-ARD and the swap aircraft A6-ANO on one time axis before and after the option. The table lists every flight the option touches over the next 7 days. Knock-on delay is propagated with measured minimum turn times, and the method was backtested on 1,634 real delays.");
}

// 5. Challenge 2
{
  const s = content(SEC1, "CHALLENGE 2 · INTELLIGENT FLIGHT RECOVERY", "Every recovery option costed and compared");
  const a = shot(s, "d-options", 0.6, 1.65, 7.6, 2.95, { alt: "Six recovery options for G9519 with delay, flights delayed, passengers delayed, missed connections, EU261 and cost" });
  shot(s, "d-strat", 0.6, a.b + 0.2, 7.6, 6.75 - a.b - 0.2, { alt: "Strategies compared: lowest cost, protect passengers, least delay" });
  const cb = criteria(s, 8.6, 1.6, 4.15, [
    "Downstream flights affected by an aircraft delay",
    "Alternative delay and recovery scenarios",
    "Recommended recovery strategy",
    "Trade-offs: disruption, passengers, cost",
    "Minimised cascade across the network",
  ]);
  bullets(s, [
    [B("Option types: "), { text: "absorb, same-type swap, hold a connection, cancel or consolidate a round trip" }],
    [B("Cost model: "), { text: "delay minutes, care, EU261, missed-connection handling" }],
    [B("Strategies: "), { text: "lowest cost, protect passengers, least delay re-rank the same options" }],
  ], { x: 8.6, y: cb, w: 4.15, h: 6.75 - cb, fontSize: 13 });
  s.addNotes("For G9519 the engine produced six options. Lowest cost picks the swap with A6-ANO at AED 127,350; protect passengers and least delay pick the swap with A6-ARI, which breaks 83 connections instead of 100. Clicking a strategy card changes the recommendation.");
}

// 6. Challenge 3
{
  const s = content(SEC1, "CHALLENGE 3 · PASSENGER RECOVERY", "Find who will misconnect and rebook them on real seats");
  const a = shot(s, "d-pax", 0.6, 1.65, 7.6, 2.55, { alt: "Connecting passengers at risk with planned and new connection, MCT, slack, miss risk and proposed rebooking" });
  shot(s, "d-reb", 0.6, a.b + 0.2, 7.6, 6.75 - a.b - 0.2, { alt: "98 rebooked within 24 hours, 2 without a seat, priority weights and passengers with care plans" });
  const cb = criteria(s, 8.6, 1.6, 4.15, [
    "Passengers likely to miss connections",
    "Alternatives by availability and MCT",
    "High-value customers, families with infants",
    "Itineraries, group bookings, inventory",
    "Minimised inconvenience, personal messages",
  ]);
  bullets(s, [
    [B("Slack = connection − MCT "), { text: "per passenger, with predicted miss risk" }],
    [B("CP-SAT rebooking "), { text: "keeps bookings together and never exceeds free seats; optimal in under 1 s" }],
    [B("Care plan "), { text: "for every wait: meals, hotel, transport, refund option, transit-visa flag" }],
  ], { x: 8.6, y: cb, w: 4.15, h: 6.75 - cb, fontSize: 13 });
  s.addNotes("For G9519, 100 connections break under the recommended option. 98 passengers are rebooked on later flights within 24 hours and 2 get a next-day seat with a hotel or a refund. Every passenger gets a care plan and a message draft.");
}

// 7. Prioritisation
{
  const s = content(SEC1, "AI-DRIVEN PASSENGER PRIORITISATION", "Transparent, configurable priority when seats run out");
  const a = shot(s, "c-top", 0.6, 1.65, 6.3, 2.05, { alt: "G9800 SHJ to KUL cancelled: 31 free seats, 157 without a seat, tier counts" });
  shot(s, "c-explain", 0.6, a.b + 0.2, 6.3, 6.75 - a.b - 0.2, { alt: "Priority weights sliders and a passenger's score breakdown, tier reason and message" });
  const cb = criteria(s, 7.3, 1.6, 5.45, [
    "Prioritise dynamically with multiple attributes",
    "Frequent travellers without loyalty membership",
    "Commercial value vs inconvenience and feasibility",
    "Recommend options when seats are insufficient",
    "Explain why a passenger is prioritised",
    "Change weights and see recommendations respond",
    "Rights and assistance independent of score",
  ]);
  bullets(s, [
    [B("Tiers first: "), { text: "mandated care (assistance, infants) → urgent connections → standard → non-revenue last" }],
    [B("Weighted score inside a tier: "), { text: "loyalty, frequency, fare and booking class, ancillaries, journey, family / group" }],
    [B("G9800 cancelled: "), { text: "188 passengers, 31 seats; 157 get hotel, next-day seat or refund" }],
  ], { x: 7.3, y: cb, w: 5.45, h: 6.75 - cb, fontSize: 13 });
  s.addNotes("The passenger shown is in tier 1 because they travel with an infant, and is not a loyalty member, yet still ranks first; the score breakdown shows each attribute's points. Moving a weight slider and pressing re-run re-orders passengers inside each tier; the tier rules never change.");
}

// 8. Challenge 4
{
  const s = content(SEC1, "CHALLENGE 4 · AI-DRIVEN DECISION SUPPORT", "Explained recommendations that a person approves");
  const a = shot(s, "d-explain", 0.6, 1.65, 7.6, 2.0, { alt: "Passenger priority score with contributing attributes, reason and message draft" });
  const b = shot(s, "d-why", 0.6, a.b + 0.25, 4.2, 1.5, { alt: "Why this recommendation, written by Claude from engine facts" });
  shot(s, "d-crew", 0.6, b.b + 0.25, 7.6, 6.75 - b.b - 0.25, { alt: "Crew FDP alert in the scenario" });
  const cb = criteria(s, 8.6, 1.6, 4.15, [
    "Consolidated flight and passenger impact",
    "Compare scenarios and expected outcomes",
    "Explain AI recommendations",
    "Simulate changes before taking action",
    "Scores and contributing attributes",
    "Configurable strategies",
  ]);
  bullets(s, [
    [B("Human in control: "), { text: "approve, or override with a required reason; every decision audited" }],
    [B("AI agent "), { text: "investigates a flight with read-only engine tools and proposes one option" }],
    [B("Messages: "), { text: "template per passenger, optional AI personalisation" }],
  ], { x: 8.6, y: cb, w: 4.15, h: 6.75 - cb, fontSize: 13 });
  s.addNotes("One screen holds the KPIs, the strategies, the options, the crew alert, the rotation, the affected flights and the passengers. Claude writes the explanation from engine facts only. Nothing changes in airline systems: a person approves or overrides, and the audit trail records it. As of now the distinct roles are OCC and Evaluator; the PCU role has the same access as OCC.");
}

// 9. AI techniques, delivery, benefits
{
  const s = content(SEC1, "AI TECHNIQUES, DELIVERY AND BUSINESS BENEFITS (§7, §8)", "Five AI techniques, each with a clear job");
  const tech = [
    ["Predictive", "LightGBM delay risk with SHAP reasons; misconnection risk"],
    ["Optimisation", "OR-Tools CP-SAT rebooking; costed option search"],
    ["Generative", "Claude explains engine facts, drafts messages"],
    ["Agentic", "Claude agent calls read-only engine tools, ≤12 calls / 120 s"],
    ["Scoring + what-if", "Configurable weighted priority, strategy switch"],
  ];
  tech.forEach(([h, b], i) => {
    const y = 1.62 + i * 0.68;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { objectName: "Tech " + h, x: 0.6, y, w: 6.0, h: 0.58, rectRadius: 0.06, fill: { color: i % 2 ? C.background2 : "E6EEFA" }, line: { color: i % 2 ? C.background2 : "E6EEFA", width: 0 } });
    T(s, h, { x: 0.78, y, w: 1.7, h: 0.58, fontSize: 13, bold: true, color: C.accent1, valign: "middle" });
    T(s, b, { x: 2.5, y, w: 4.0, h: 0.58, fontSize: 12, valign: "middle" });
  });
  card(s, 0.6, 5.1, 6.0, 1.65, "Delivered on the provided VM", "Docker Compose: UI on :8080 (nginx + React), API on :8888 (FastAPI), PostgreSQL, Parquet + DuckDB. Smoke 15/15 and Playwright 11/11 on the live server; 136 backend + 46 frontend tests; rollback point before each deploy.", { bodySize: 12 });
  card(s, 6.9, 1.62, 5.85, 2.35, "Business benefits", "", { fill: "E7F4EC", headColor: C.accent3 });
  bullets(s, [
    "One shared picture for OCC and PCU instead of three",
    "Recovery cost made visible: AED 292k between best and worst option on G9519",
    "Fair, explainable passenger treatment; legal care always first",
    "Earlier action from 7-day risk instead of on-the-day firefighting",
  ], { x: 7.1, y: 2.12, w: 5.45, h: 1.8, fontSize: 12 });
  card(s, 6.9, 4.15, 5.85, 2.6, "Responsible design and implementation", "", { fill: "FDE8EC", headColor: C.accent2 });
  bullets(s, [
    "Recommend only; engine computes every number, the AI never decides",
    "No names, booking refs, IDs or contacts sent to the AI (tested)",
    "Fallbacks: template text and a rule-based planner if the AI fails",
    "Next: HTTPS + backups, partner carriers, live data feeds, airline SSO",
  ], { x: 7.1, y: 4.65, w: 5.45, h: 2.0, fontSize: 12 });
  s.addNotes("UC5 deliverables: a working prototype on the provided VM, a live demo with real data and two scenarios, weighted prioritisation, the AI techniques and their contribution, and the business benefits and implementation considerations. Test figures: Playwright 11/11 on the server is from the Model Card release; the backend and frontend counts are from the latest local gate.");
}

// =================== Extras (slides 10-13) ===================
pres.addSection({ title: "Beyond UC5" });
const SEC2 = "Beyond UC5";

// 10. Crew FDP
{
  const s = content(SEC2, "BEYOND UC5 · CREW FDP ALERTS", "Spot recovery options that break crew duty limits");
  const a = shot(s, "d-crew", 0.6, 1.65, 7.8, 2.0, { alt: "Crew FDPs: 1 of 6 options takes a crew past its maximum flight duty period" });
  shot(s, "e-crew", 0.6, a.b + 0.25, 7.8, 6.75 - a.b - 0.25, { alt: "Model Card crew FDP headroom: 35,021 duties, median 275 min, effect of extra delay, by crew type" });
  const x = 8.8, w = 3.95;
  stat(s, x, 1.6, w, "1 of 6", "options on G9519 breaks a maximum FDP: G9552 captain 1 min over (swap A6-AQG)", C.accent2);
  T(s, "How it works", { x, y: 2.9, w, h: 0.3, fontSize: 15, bold: true, color: C.text2 });
  bullets(s, [
    [B("Headroom "), { text: "= max FDP − planned FDP of the tightest crew member, from the roster (crew names removed)" }],
    [B("No roster? "), { text: "10th percentile of the flight number's history, labelled estimated" }],
    [B("Each option "), { text: "is checked flight by flight: ok, tight (< 30 min) or breach" }],
    [B("Alert only: "), { text: "crew control decides; the agent reports breaches as risks" }],
    [B("Roster analysis: "), { text: "35,021 G9 duties, median headroom 275 min; pilots tightest (28–29 min); +60 min pushes 4.3% of duties over" }],
  ], { x, y: 3.25, w, h: 3.5, fontSize: 12 });
  s.addNotes("UC5 does not ask for crew, but a recovery option that breaks crew duty limits is not feasible. The check uses the crew roster with names removed. Here the swap with A6-AQG would take a captain 1 minute past the maximum FDP; the recommended swap does not breach. The section appears only when an option breaches.");
}

// 11. Rewards
{
  const s = content(SEC2, "BEYOND UC5 · PASSENGER GOODWILL REWARDS", "The right goodwill gesture per passenger, within a budget");
  const a = shot(s, "r-plan", 0.6, 1.65, 7.6, 3.4, { alt: "Reward plan for G9519 within an AED 5,000 budget: 54 of 166 passengers rewarded" });
  shot(s, "r-more", 0.6, a.b + 0.25, 7.6, 6.75 - a.b - 0.25, { alt: "Why this reward: severity, value, target and chance of acceptance" });
  const x = 8.6, w = 4.15;
  stat(s, x, 1.6, 1.9, "54 / 166", "passengers rewarded within AED 5,000", C.accent3);
  stat(s, x + 2.15, 1.6, 2.0, "76%", "predicted acceptance of the top lounge pass", C.accent3);
  bullets(s, [
    [B("Severity "), { text: "0–100 from delay, cancellation, missed connection, wait and vulnerability" }],
    [B("Value "), { text: "from the recovery-priority score; upcoming trips raise the chance a voucher is used" }],
    [B("Choice: "), { text: "meal, voucher, lounge, miles or ticket by severity × value × acceptance; never over budget" }],
    [B("Acceptance model: "), { text: "LightGBM on simulated redemption history (AUC 0.70 vs 0.665 rules), labelled as simulated" }],
    [B("Separate from legal care; "), { text: "nothing is sent to passengers" }],
  ], { x, y: 2.85, w, h: 3.9, fontSize: 12 });
  s.addNotes("A planner enters a goodwill budget and the system recommends a reward per passenger. For G9519 the full plan would cost AED 34,420; with AED 5,000 it scales down and rewards 54 passengers. The preference model is trained on simulated data because no real redemption history exists, and the app says so.");
}

// 12. 7-day prediction
{
  const s = content(SEC2, "BEYOND UC5 · 7-DAY DELAY PREDICTION", "Know which flights will run late before the day");
  const a = shot(s, "w-list", 0.6, 1.65, 6.4, 3.3, { alt: "Delay watchlist: 214 flights, 36 high risk, 178 medium, 2,174 expected missed connections" });
  shot(s, "w-detail", 0.6, a.b + 0.2, 6.4, 6.75 - a.b - 0.2, { alt: "G9406 BOM to SHJ: reasons and connecting passengers most at risk" });
  s.addChart(pres.charts.BAR, [
    { name: "LightGBM model", labels: ["15+ min delay", "60+ min delay"], values: [0.801, 0.770] },
    { name: "Route × hour baseline", labels: ["15+ min delay", "60+ min delay"], values: [0.741, 0.676] },
  ], {
    x: 7.35, y: 1.55, w: 5.4, h: 2.55, barDir: "col", barGapWidthPct: 60,
    chartColors: [HEX.accent1, "B8C4D8"],
    showTitle: true, title: "Ranking quality (AUC) on 5,956 unseen flights", titleFontSize: 12, titleColor: HEX.dk2, titleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11, dataLabelColor: HEX.dk1, dataLabelFormatCode: "0.000", dataLabelFontFace: "+mn-lt",
    valAxisMinVal: 0.5, valAxisMaxVal: 0.85, valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    catAxisLabelColor: HEX.accent5, catAxisLabelFontSize: 11, catAxisLabelFontFace: "+mn-lt",
    showLegend: true, legendPos: "b", legendFontSize: 10, legendColor: HEX.accent5, legendFontFace: "+mn-lt",
  });
  bullets(s, [
    [B("Every flight, 7 days out: "), { text: "chance of a 15+ and 60+ min delay, a planning delay, expected missed connections" }],
    [B("Reasons in plain words "), { text: "from SHAP, and the connecting passengers most at risk" }],
    [B("Calibrated: "), { text: "no-slack connections predicted 70% missed, 69% were" }],
    [B("Cascade check: "), { text: "1,656 real pairs last month, 93% within 30 min of the formula" }],
    [B("One click "), { text: "opens a pre-filled delay scenario or asks the agent" }],
  ], { x: 7.35, y: 4.3, w: 5.4, h: 2.45, fontSize: 12 });
  s.addNotes("Trained on about 57,000 G9 flights from January to October 2026 using only what is known a week ahead, and tested on the following four weeks. The baseline is the past late rate of the same route at the same hour. A prediction is not a decision: it ranks flights and pre-fills a scenario.");
}

// 13. Evaluator mode
{
  const s = content(SEC2, "BEYOND UC5 · EVALUATOR MODE", "Test it with your own flights, and check the evidence");
  const a = shot(s, "e-test", 0.6, 1.65, 6.4, 5.1, { alt: "Test data page: flights and passengers sheet columns, templates, Check files and Add to system" });
  const m = shot(s, "e-model", 7.35, 1.65, 5.4, 1.2, { alt: "Model Card overview: AUC 0.770 at +60 min, +9.3 pp vs baseline" });
  const q = shot(s, "e-perf", 7.35, m.b + 0.2, 5.4, 1.75, { alt: "Model performance by delay threshold vs baseline" });
  bullets(s, [
    [B("Roles today: "), { text: "OCC and Evaluator are the distinct roles; Evaluator also sees Model Card and Test data (enforced by the server). PCU has the same access as OCC" }],
    [B("Your own flights: "), { text: "two CSV sheets from the template; Check files stores nothing, Add to system makes them searchable in seconds" }],
    [B("Scored, not retrained; "), { text: "Remove test data restores the real data" }],
    [B("Model Card: "), { text: "performance by threshold, calibration, alert cut-offs, model comparison and tuning, reward model, cascade check, crew FDP analysis" }],
  ], { x: 7.35, y: q.b + 0.25, w: 5.4, h: 6.75 - q.b - 0.25, fontSize: 12 });
  s.addNotes("Evaluator mode lets judges bring one or two flights of their own and run delay, cancellation and reward scenarios on them without touching the real data or retraining models. The Model Card shows all model evidence in one place.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
