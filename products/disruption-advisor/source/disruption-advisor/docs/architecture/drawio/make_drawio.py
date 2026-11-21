"""Generate the aeroRecovery design diagrams as draw.io files (as built, 21 Nov 2026)."""
import html, itertools, pathlib, sys
OUT = pathlib.Path(sys.argv[1])
S = {
 "app":   "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE6EB;strokeColor=#D6002F;fontColor=#1F2124;",
 "svc":   "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#D6002F;fontColor=#1F2124;",
 "job":   "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF5F7;strokeColor=#D6002F;dashed=1;fontColor=#1F2124;",
 "ext":   "rounded=1;whiteSpace=wrap;html=1;fillColor=#F1F3F4;strokeColor=#5F6368;fontColor=#1F2124;",
 "later": "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#9AA0A6;dashed=1;fontColor=#5F6368;",
 "actor": "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;fillColor=#FFE6EB;strokeColor=#D6002F;",
 "db":    "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;size=10;fillColor=#E8F0FE;strokeColor=#1A73E8;fontColor=#1F2124;",
 "file":  "shape=note;whiteSpace=wrap;html=1;size=12;fillColor=#FEF7E0;strokeColor=#B06000;fontColor=#1F2124;",
 "step":  "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#5F6368;fontColor=#1F2124;",
 "dec":   "rhombus;whiteSpace=wrap;html=1;fillColor=#FEF7E0;strokeColor=#B06000;fontColor=#1F2124;",
 "ok":    "rounded=1;whiteSpace=wrap;html=1;fillColor=#E6F4EA;strokeColor=#1E8E3E;fontColor=#1F2124;",
 "group": "rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#9AA0A6;dashed=1;verticalAlign=top;align=left;spacingLeft=8;fontStyle=1;fontColor=#5F6368;",
 "title": "text;html=1;align=left;verticalAlign=middle;fontSize=18;fontStyle=1;fontColor=#1F2124;",
 "note":  "text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;fontSize=11;fontColor=#5F6368;",
}
EDGE = "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;endFill=1;strokeColor=#5F6368;fontSize=10;fontColor=#1F2124;labelBackgroundColor=#FFFFFF;"

class D:
    def __init__(s, name, title, note=""):
        s.name, s.cells, s.ids = name, [], itertools.count(2)
        s.box(title, "title", 20, 10, 900, 30)
        if note: s.box(note, "note", 20, 40, 1100, 30)
    def box(s, label, kind, x, y, w=150, h=50):
        i = f"c{next(s.ids)}"
        s.cells.append(f'<mxCell id="{i}" value="{html.escape(label)}" style="{S[kind]}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return i
    def edge(s, a, b, label="", dashed=False, exit=None, entry=None):
        i = f"c{next(s.ids)}"
        st = EDGE + ("dashed=1;" if dashed else "")
        if exit: st += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
        if entry: st += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
        s.cells.append(f'<mxCell id="{i}" value="{html.escape(label)}" style="{st}" edge="1" parent="1" source="{a}" target="{b}"><mxGeometry relative="1" as="geometry"/></mxCell>')
    def save(s):
        body = "".join(s.cells)
        xml = (f'<mxfile host="app.diagrams.net"><diagram name="{s.name}" id="{s.name}"><mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" '
               f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1400" pageHeight="900" math="0" shadow="0">'
               f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>{body}</root></mxGraphModel></diagram></mxfile>')
        (OUT / f"{s.name}.drawio").write_text(xml)

br = "<br>"
# 1 System context
d = D("aero-recovery-1-context", "1  System context", "Who uses aeroRecovery and what it talks to. The AI service receives only minimised fields: no names, booking references or contact details.")
occ = d.box("OCC controller", "actor", 60, 130, 40, 70); pcu = d.box("PCU agent", "actor", 60, 300, 40, 70)
app = d.box(f"<b>aeroRecovery</b>{br}impact · recovery options · priority ·{br}rebooking · care · rewards · prediction · agent{br}(recommend only)", "app", 400, 200, 320, 110)
d.edge(occ, app, "assess delays, compare and approve recovery", exit=(1, 0.5), entry=(0, 0.3))
d.edge(pcu, app, "prioritise, rebook, approve messages and rewards", exit=(1, 0.5), entry=(0, 0.7))
ext = d.box(f"Airline extracts{br}rotation · schedule · inventory · MCT ·{br}punctuality · bookings (name-free)", "file", 360, 420, 250, 70)
tz = d.box(f"Public airport{br}time-zone dataset", "file", 640, 420, 150, 70)
d.edge(ext, app, "batch ingest", exit=(0.5, 0), entry=(0.3, 1)); d.edge(tz, app, "ingest", exit=(0.5, 0), entry=(0.85, 1))
cl = d.box(f"Anthropic Claude API{br}explanations · message drafts · agent", "ext", 880, 140, 240, 70)
d.edge(app, cl, "engine facts only", exit=(1, 0.3), entry=(0, 0.5))
sysx = d.box(f"Airline systems (later){br}events · real loyalty / SSR · crew · PSS write-back", "later", 880, 290, 260, 70)
d.edge(app, sysx, "phase 4", dashed=True, exit=(1, 0.75), entry=(0, 0.5))
d.save()

# 2 Containers and deployment
d = D("aero-recovery-2-containers", "2  Containers and deployment (Docker Compose on the OCI VM)", "Long-running services restart unless stopped; Docker starts at boot. One-shot jobs run on start-up and skip unchanged work. HTTPS (Caddy) and nightly backups are phase 6.")
cl = d.box("Anthropic Claude API", "ext", 520, 85, 180, 45)
d.box("OCI VM eu-frankfurt-1 · 8 vCPU · 62 GiB · Oracle Linux 10", "group", 140, 150, 1180, 560)
b = d.box("Browser (OCC / PCU)", "actor", 50, 330, 40, 70)
web = d.box(f"<b>web</b>{br}nginx :8888 · React app{br}CSP · login rate limit", "svc", 170, 320, 190, 80)
api = d.box(f"<b>api</b>{br}FastAPI · uvicorn{br}scenarios · risk · agent · decisions", "svc", 430, 320, 210, 80)
mig = d.box(f"<b>migrate</b> (one-shot){br}Alembic", "job", 430, 190, 150, 55)
pg = d.box(f"<b>db</b> PostgreSQL 18{br}scenarios · decisions · agent_runs{br}schema <i>extracts</i> (27.9M bookings)", "db", 760, 180, 260, 100)
ops = d.box(f"<b>ops-data</b> volume{br}Parquet raw/ + ops/{br}read by in-memory DuckDB", "db", 760, 470, 260, 100)
inp = d.box(f"Input files (read-only){br}~/disruption-advisor-input", "file", 170, 600, 210, 60)
ing = d.box(f"<b>ingest</b> (one-shot){br}stages 1 · 2 · 3 · 3b · 4", "job", 450, 600, 180, 60)
xdb = d.box(f"<b>extracts-db</b> (one-shot){br}raw/ → PostgreSQL extracts", "job", 1100, 330, 190, 70)
d.edge(b, web, "HTTP :8888", exit=(1, 0.5), entry=(0, 0.5)); d.edge(web, api, "/api", exit=(1, 0.5), entry=(0, 0.5))
d.edge(api, cl, "HTTPS", exit=(0.85, 0), entry=(0.5, 1))
d.edge(mig, pg, exit=(1, 0.5), entry=(0, 0.3)); d.edge(api, pg, "SQLAlchemy", exit=(1, 0.25), entry=(0, 0.75))
d.edge(api, ops, "DuckDB read-only", exit=(1, 0.75), entry=(0, 0.25))
d.edge(inp, ing, exit=(1, 0.5), entry=(0, 0.5)); d.edge(ing, ops, exit=(1, 0.5), entry=(0, 0.75))
d.edge(ops, xdb, exit=(1, 0.5), entry=(0.5, 1)); d.edge(xdb, pg, exit=(0.5, 0), entry=(1, 0.5))
d.box(f"Secrets: settings.env on the server (mode 600) · Ports: 8888 app · 22 SSH · 80/443 reserved for HTTPS", "note", 170, 675, 700, 25)
d.save()

# 3 Components (layered)
d = D("aero-recovery-3-components", "3  Components inside the API (modular monolith)", "Entry points start an analysis; the engine computes impact, options, priority and rebooking; the output layer explains and records decisions. Every module is recommend-only.")
ge = d.box("Entry points", "group", 20, 90, 280, 560)
gn = d.box("Engine", "group", 330, 90, 690, 560)
go = d.box("Output", "group", 1050, 90, 260, 560)
e = [("<b>auth</b><br>demo roles OCC / PCU", 130), ("<b>scenarios</b><br>delay or cancellation", 240), ("<b>risk</b><br>delay model · watchlist ·<br>missed-connection risk", 350), ("<b>agent</b><br>Claude tool loop (≤12 calls, 120 s)<br>planner fallback", 470)]
for lbl, y in e: d.box(lbl, "svc", 40, y, 240, 80)
eng = [("<b>network</b><br>rotation · turn times 51/36 min<br>propagation · swaps · round trips", 350, 130), ("<b>passengers</b><br>connections 15 min–20 h<br>MCT · missed connections", 690, 130),
       ("<b>recovery</b><br>absorb · swap · cancel · consolidate", 350, 240), ("<b>strategy</b><br>lowest cost · protect passengers ·<br>least delay", 690, 240),
       ("<b>priority</b><br>tiers + weighted score + reasons", 350, 350), ("<b>rebooking</b><br>CP-SAT, bookings kept together", 690, 350),
       ("<b>cost + care</b><br>delay · EU261 · meals · hotel ·<br>transport · refund option", 350, 470), ("<b>rewards</b><br>severity × value × acceptance<br>within a budget", 690, 470)]
for lbl, x, y in eng: d.box(lbl, "app", x, y, 310, 80)
o1 = d.box("<b>explain</b><br>Claude or templates<br>narrative · message drafts", "svc", 1070, 200, 220, 90)
o2 = d.box("<b>decisions</b><br>approve · reject · override<br>audit trail", "ok", 1070, 400, 220, 90)
d.edge(o1, o2, exit=(0.5, 1), entry=(0.5, 0))
d.edge(ge, gn, "start", exit=(1, 0.5), entry=(0, 0.5)); d.edge(gn, go, "facts", exit=(1, 0.5), entry=(0, 0.5))
d.box("Data: ops Parquet (DuckDB, read-only) · PostgreSQL (scenarios, decisions, agent runs)", "note", 330, 660, 700, 25)
d.save()

# 4 Data pipeline
d = D("aero-recovery-4-data", "4  Data pipeline and data model", "The ingest runs the stages in order and skips work whose inputs and code are unchanged. The API only reads the ops Parquet; PostgreSQL holds what people create plus a copy of the extracts.")
inputs = d.box("<b>Input files (read-only)</b><br>Flight Rotation.xls<br>Flight Schedule.csv<br>Flight Inventory.csv<br>Connection Time.xlsx<br>Punctuality Jan–Nov 2026.xlsx<br>Bookings Parquet (name-free, by month)<br><i>or the original zip</i>", "file", 30, 100, 250, 170)
s1 = d.box(f"<b>Stage 1 · convert</b>{br}typed Parquet · names removed{br}bookings by departure month", "job", 330, 145, 220, 80)
raw = d.box(f"<b>raw/</b>{br}rotation · schedule · inventory · mct ·{br}punctuality · bookings (27.9M)", "db", 600, 135, 250, 100)
xdb = d.box(f"<b>extracts-db</b>{br}→ PostgreSQL schema extracts", "job", 920, 150, 230, 70)
tz = d.box("Airport time zones (public, bundled)", "file", 30, 340, 250, 50)
syn = d.box(f"Synthetic, labelled:{br}loyalty tier · fare family · SSR codes ·{br}passenger IDs · demo G9901", "ext", 30, 420, 250, 70)
s2 = d.box(f"<b>Stage 2 · operating picture</b>{br}window 19–30 Nov · G9 only{br}history 1 Jan – 18 Nov", "job", 600, 330, 250, 80)
ops = d.box(f"<b>ops/</b>{br}flights 2,614 · pax_segments 299k · customers ·{br}aircraft · mct · airports · history 63k", "db", 920, 320, 300, 100)
s3 = d.box(f"<b>Stage 3</b> delay-risk model{br}flight_risk · connection_risk · model card", "job", 920, 480, 300, 60)
s3b = d.box("<b>Stage 3b</b> cascade check (last month)", "job", 920, 560, 300, 45)
s4 = d.box("<b>Stage 4</b> reward acceptance model (simulated history)", "job", 920, 625, 300, 45)
d.edge(inputs, s1, exit=(1, 0.5), entry=(0, 0.5)); d.edge(s1, raw, exit=(1, 0.5), entry=(0, 0.5)); d.edge(raw, xdb, exit=(1, 0.5), entry=(0, 0.5))
d.edge(raw, s2, exit=(0.5, 1), entry=(0.5, 0)); d.edge(tz, s2, exit=(1, 0.5), entry=(0, 0.35)); d.edge(syn, s2, dashed=True, exit=(1, 0.5), entry=(0, 0.75))
d.edge(s2, ops, exit=(1, 0.5), entry=(0, 0.5)); d.edge(ops, s3, exit=(0.5, 1), entry=(0.5, 0))
d.edge(ops, s3b, exit=(0, 0.8), entry=(0, 0.5)); d.edge(ops, s4, exit=(1, 0.8), entry=(1, 0.5))
d.save()

def snake(d, steps, y0, w=250, h=85, gap=50, kinds=None):
    """Two rows of four: row 1 left to right, row 2 right to left, so no arrow crosses a box."""
    ids = []
    for k, (t, kind) in enumerate(steps):
        col = k % 4 if k < 4 else 3 - (k % 4)
        x = 40 + col * (w + gap); y = y0 + (k // 4) * 220
        ids.append(d.box(t, kind, x, y, w, h + (25 if kind == "dec" else 0)))
    for k in range(len(ids) - 1):
        if k == 3: d.edge(ids[k], ids[k + 1], exit=(0.5, 1), entry=(0.5, 0))
        elif k < 3: d.edge(ids[k], ids[k + 1], exit=(1, 0.5), entry=(0, 0.5))
        else: d.edge(ids[k], ids[k + 1], exit=(0, 0.5), entry=(1, 0.5))
    return ids

# 5 Scenario A
d = D("aero-recovery-5-delay", "5  Scenario A: delay", "An inbound flight is late. The engine propagates the delay along the aircraft, re-checks every connection, builds and costs the options, and the strategy picks the recommendation.")
snake(d, [
 ("OCC picks a flight and a delay<br>(or opens it from the 7-day watchlist)", "ext"),
 ("Propagate along the aircraft rotation for 7 days<br>(turn 51 min SHJ, 36 min outstations)", "step"),
 ("Re-check every connection<br>(MCT; 15 min – 20 h)", "step"),
 ("Build options: absorb · same-type swap (≤3) ·<br>cancel a later round trip (≤3) ·<br>consolidate if all fit within 6 h", "step"),
 ("Cost each option: delay · care · EU261 ·<br>rebooking of passengers left behind", "step"),
 ("Strategy picks the recommendation:<br>lowest cost · protect passengers ·<br>least delay", "dec"),
 ("Explain in plain language<br>(Claude or template)", "step"),
 ("Person approves, rejects, or<br>overrides with a reason → audit trail", "ok"),
], 110)
d.box("Also on screen: before/after rotation board · passenger tab (new flight, care, flags, message) · rewards tab (budget)", "note", 40, 450, 1000, 25)
d.save()

# 6 Scenario B
d = D("aero-recovery-6-cancellation", "6  Scenario B: cancellation with too few seats", "Passengers are ranked transparently and rebooked within the seats actually free; the planner can change the weights and re-run.")
ids = snake(d, [("PCU agent: flight G9xxx cancelled", "ext"), ("Affected passengers and their attributes", "step"),
         ("Tier + weighted score<br>+ points per attribute", "step"), ("Alternatives: G9 flights, same route or legal<br>SHJ connection, within 24 h, free seats", "step"),
         ("CP-SAT assignment:<br>bookings kept together", "step"), ("No seat → next day + hotel + meals<br>(care rules)", "step"),
         ("Reasons, message drafts,<br>reward plan within a budget", "step"), ("Approve plan, messages, rewards<br>→ audit trail", "ok")], 110)
w = d.box("What-if: change the priority weights<br>→ re-run ranking and rebooking", "dec", 40, 470, 250, 100)
d.edge(ids[7], w, "re-runs from the ranking step", dashed=True, exit=(0.5, 1), entry=(0.5, 0))
d.save()

# 7 Priority
d = D("aero-recovery-7-priority", "7  Passenger priority logic", "Legal and care duties come first. The weighted score only orders passengers inside a tier. Unaccompanied minors are out of scope (phase 4).")
a = d.box("Affected passenger", "ext", 40, 130, 160, 50)
f = d.box("Feasible alternative?<br>seats · MCT · same booking", "dec", 250, 105, 200, 100)
n = d.box("Next day + hotel + meals<br>(EU261 care if departing the EU)", "step", 250, 270, 200, 60)
t1 = d.box("Tier 1: mandated care?<br>WCHR/WCHS/WCHC · BLND · DEAF ·<br>MEDA · PREG · infant in booking", "dec", 510, 90, 260, 130)
t2 = d.box("Tier 2: urgency?<br>onward connection · last flight<br>of the day · long journey", "dec", 510, 270, 260, 130)
b1 = d.box("Band 1", "ok", 830, 130, 110, 50); b2 = d.box("Band 2", "ok", 830, 310, 110, 50); b3 = d.box("Band 3", "ok", 830, 450, 110, 50)
sc = d.box("Weighted score inside the band:<br>loyalty · frequency · fare ·<br>ancillaries · journey · family/group", "step", 1000, 230, 240, 150)
nr = d.box("Non-revenue?<br>→ after all revenue passengers", "dec", 1000, 440, 240, 100)
out = d.box("Ordered list + reasons", "ok", 1025, 590, 190, 50)
d.edge(a, f, exit=(1, 0.5), entry=(0, 0.5)); d.edge(f, n, "no", exit=(0.5, 1), entry=(0.5, 0)); d.edge(f, t1, "yes", exit=(1, 0.5), entry=(0, 0.5))
d.edge(t1, b1, "yes", exit=(1, 0.5), entry=(0, 0.5)); d.edge(t1, t2, "no", exit=(0.5, 1), entry=(0.5, 0))
d.edge(t2, b2, "yes", exit=(1, 0.5), entry=(0, 0.5)); d.edge(t2, b3, "no", exit=(0.5, 1), entry=(0, 0.5))
d.edge(b1, sc, exit=(1, 0.5), entry=(0, 0.2)); d.edge(b2, sc, exit=(1, 0.5), entry=(0, 0.55)); d.edge(b3, sc, exit=(1, 0.5), entry=(0, 0.85))
d.edge(sc, nr, exit=(0.5, 1), entry=(0.5, 0)); d.edge(nr, out, exit=(0.5, 1), entry=(0.5, 0))
d.save()

# 8 Predict, agent, rewards
d = D("aero-recovery-8-predict-agent-rewards", "8  Prediction, agent and rewards (phases 2, 3 and 5)", "Predictions rank and pre-fill; the agent investigates; rewards stay within a budget. A person decides in every case.")
d.box("Phase 2 · 7-day watchlist", "group", 20, 80, 1180, 170)
h = d.box("History Jan – 18 Nov<br>63k flights", "db", 40, 120, 150, 80)
m = d.box("LightGBM per threshold<br>5 · 15 · 30 · 60 · 120 · 180 min<br>features known 7 days ahead", "app", 230, 115, 220, 90)
r = d.box("flight risk + TreeSHAP reasons<br>planning delay (20% exceed)", "step", 490, 120, 210, 80)
c = d.box("missed-connection risk per passenger<br>arrival vs onward departure curves", "step", 740, 120, 220, 80)
wl = d.box("Watchlist ranked by expected<br>missed connections → open scenario", "ok", 990, 120, 190, 80)
d.edge(h, m); d.edge(m, r); d.edge(r, c); d.edge(c, wl)
d.box("Phase 3 · recommend-only agent", "group", 20, 280, 1180, 170)
u = d.box("Planner asks the agent<br>to investigate a flight", "ext", 40, 320, 170, 80)
l = d.box("Claude tool loop<br>read-only engine tools<br>≤12 calls · 120 s", "app", 250, 320, 200, 80)
p = d.box("Planner fallback<br>(no AI or error)", "later", 250, 410, 200, 35)
tr = d.box("Live trace of steps<br>(saved as an agent run)", "step", 490, 320, 200, 80)
o = d.box("Recommended option =<br>an engine option, saved as a scenario", "step", 730, 320, 230, 80)
ap = d.box("Person approves<br>or overrides", "ok", 990, 320, 190, 80)
d.edge(u, l); d.edge(l, tr); d.edge(tr, o); d.edge(o, ap); d.edge(u, p, "no AI", dashed=True, exit=(0.5, 1), entry=(0, 0.5))
d.box("Phase 5 · goodwill rewards", "group", 20, 480, 1180, 170)
sv = d.box("Severity 0–100<br>delay · cancellation · missed connection ·<br>wait · vulnerable", "step", 40, 520, 230, 90)
va = d.box("Passenger value 0–100<br>priority score rank", "step", 300, 520, 180, 90)
ac = d.box("Acceptance P(accept)<br>LightGBM on simulated history<br>(proxy rules fallback)", "app", 510, 520, 220, 90)
bu = d.box("Choose type and amount<br>fit the budget (AED)", "step", 760, 520, 200, 90)
apr = d.box("Approve the plan<br>(nothing is sent)", "ok", 990, 520, 190, 90)
d.edge(sv, va); d.edge(va, ac); d.edge(ac, bu); d.edge(bu, apr)
d.save()
print(sorted(p.name for p in OUT.glob("*.drawio")))
