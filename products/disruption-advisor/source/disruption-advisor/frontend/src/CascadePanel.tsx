import { useEffect, useMemo, useState } from "react";
import { api, type CascadeCheck, type CascadeRow, errorText } from "./api";
import { Kpi } from "./DelayView";
import { num } from "./format";

const pct = (p: number | null | undefined): string => (p == null ? "n/a" : `${Math.round(p * 100)}%`);
const signed = (n: number | null | undefined): string => (n == null ? "n/a" : `${n > 0 ? "+" : ""}${n}`);
const CAP = 160; // the charts stop at 160 min; larger values are drawn on the edge
const BAND_COLOUR = ["var(--ok)", "var(--warn)", "#c2570c", "var(--bad)"];

/** Colour band of a delta: within 15, 15-30, 30-60, over 60 minutes (either direction). */
function band(delta: number): number {
  const d = Math.abs(delta);
  return d <= 15 ? 0 : d <= 30 ? 1 : d <= 60 ? 2 : 3;
}

/** Sidebar of the 7-day tab: the cascade formula against what really happened last month. Six boxes; the full
 * graphical view opens on demand. */
export function CascadePanel() {
  const [data, setData] = useState<CascadeCheck | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    api
      .cascade()
      .then(setData)
      .catch((e: unknown) => setError(errorText(e, "Could not load the cascade check.")));
  }, []);

  const k = data?.kpis;
  return (
    <section className="cascade" aria-labelledby="cascade-title">
      <h2 id="cascade-title">Last month: cascade formula vs actual</h2>
      {error && <p className="error">{error}</p>}
      {!data && !error && <p className="muted">Checking last month…</p>}
      {data && k && (
        <>
          <p className="small muted">
            {data.from} to {data.to}. Does a late arrival really delay the aircraft's next flight as the formula says?
          </p>
          <div className="cascade-kpis">
            <Kpi label="Cascade pairs" value={num(k.pairs)} />
            <Kpi label="Mean delta (actual − formula)" value={`${signed(k.mean_delta)} min`} />
            <Kpi label="Within ±15 min" value={pct(k.within_15_share)} />
            <Kpi label="Within ±30 min" value={pct(k.within_30_share)} />
            <Kpi label="Formula underestimates" value={num(k.underestimates)} sub="by more than 15 min" />
            <Kpi label="Formula overestimates" value={num(k.overestimates)} sub="by more than 15 min" />
          </div>
          <button type="button" onClick={() => setOpen(true)}>
            Expand the full view
          </button>
          {open && <CascadeDialog data={data} onClose={() => setOpen(false)} />}
        </>
      )}
    </section>
  );
}

function CascadeDialog({ data, onClose }: { data: CascadeCheck; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const k = data.kpis;
  return (
    <div className="overlay" role="presentation" onClick={onClose}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="cascade-dialog-title" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-head">
          <div>
            <p className="small muted">Disruption Advisor · formula validation</p>
            <h2 id="cascade-dialog-title">Cascade prediction vs actual</h2>
            <p className="small muted">
              {num(k.pairs)} cascade pairs from real G9 punctuality data, {data.from} to {data.to}. Compares the formula:{" "}
              <strong>{data.formula}</strong> against the observed departure.
            </p>
          </div>
          <button type="button" className="link" onClick={onClose} autoFocus>
            Close
          </button>
        </div>
        <div className="cascade-kpis cascade-kpis-wide">
          <Kpi label="Cascade pairs" value={num(k.pairs)} />
          <Kpi label="Mean delta (actual − formula)" value={`${signed(k.mean_delta)} min`} />
          <Kpi label="Within ±15 min" value={pct(k.within_15_share)} />
          <Kpi label="Within ±30 min" value={pct(k.within_30_share)} />
          <Kpi label="Formula underestimates" value={num(k.underestimates)} sub="by more than 15 min" />
          <Kpi label="Formula overestimates" value={num(k.overestimates)} sub="by more than 15 min" />
        </div>
        <div className="cascade-charts">
          <Scatter rows={data.rows} />
          <Histogram bins={data.histogram} />
        </div>
        {data.excluded.length > 0 && (
          <p className="small note">
            {data.excluded.length} extreme outlier{data.excluded.length > 1 ? "s" : ""} left out of the figures and charts (
            {data.excluded_rule}):{" "}
            {data.excluded.map((e) => `${e.flight} ${e.route} ${e.date}: formula ${e.formula_ko} min, actual ${e.actual_ko} min`).join("; ")}.
          </p>
        )}
        <PairsTable rows={data.rows} total={data.rows_total} />
        <p className="small muted">{data.definition}</p>
      </div>
    </div>
  );
}

function Scatter({ rows }: { rows: CascadeRow[] }) {
  const W = 520;
  const H = 320;
  const pad = { l: 44, r: 12, t: 12, b: 36 };
  const x = (v: number) => pad.l + (Math.min(v, CAP) / CAP) * (W - pad.l - pad.r);
  const y = (v: number) => H - pad.b - (Math.min(v, CAP) / CAP) * (H - pad.t - pad.b);
  const ticks = [0, 40, 80, 120, 160];
  const capped = rows.filter((r) => r.formula_ko > CAP || r.actual_ko > CAP).length;
  return (
    <figure className="chart">
      <figcaption>Formula vs actual knock-on delay (min)</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Scatter of ${rows.length} pairs: formula knock-on against actual knock-on`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} className="grid" />
            <text x={pad.l - 6} y={y(t) + 4} textAnchor="end" className="axis">{t}</text>
            <text x={x(t)} y={H - pad.b + 16} textAnchor="middle" className="axis">{t}</text>
          </g>
        ))}
        <line x1={x(0)} y1={y(0)} x2={x(CAP)} y2={y(CAP)} className="diag" />
        {rows.map((r, i) => (
          <circle key={i} cx={x(r.formula_ko)} cy={y(r.actual_ko)} r={2.6} fill={BAND_COLOUR[band(r.delta)]} fillOpacity={0.7} />
        ))}
        <text x={(pad.l + W - pad.r) / 2} y={H - 4} textAnchor="middle" className="axis">Formula knock-on (min)</text>
        <text transform={`translate(12 ${H / 2}) rotate(-90)`} textAnchor="middle" className="axis">Actual knock-on (min)</text>
      </svg>
      <div className="legend small">
        {["±15 min", "15–30 min", "30–60 min", "over 60 min"].map((l, i) => (
          <span key={l}><i style={{ background: BAND_COLOUR[i] }} /> {l}</span>
        ))}
        {capped > 0 && <span className="muted">· {capped} beyond 160 min drawn on the edge</span>}
      </div>
    </figure>
  );
}

function Histogram({ bins }: { bins: { label: string; count: number }[] }) {
  const W = 520;
  const H = 320;
  const pad = { l: 44, r: 12, t: 20, b: 36 };
  const max = Math.max(...bins.map((b) => b.count), 1);
  const bw = (W - pad.l - pad.r) / bins.length;
  const colour = ["#2b6cb0", "var(--ok)", "var(--ok)", "var(--warn)", "#c2570c", "var(--bad)"];
  return (
    <figure className="chart">
      <figcaption>Delta distribution (actual − formula, min)</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Number of pairs by delta range">
        <line x1={pad.l} x2={W - pad.r} y1={H - pad.b} y2={H - pad.b} className="grid" />
        {bins.map((b, i) => {
          const h = (b.count / max) * (H - pad.t - pad.b);
          return (
            <g key={b.label}>
              <rect x={pad.l + i * bw + 6} y={H - pad.b - h} width={bw - 12} height={h} fill={colour[i] ?? "var(--ok)"} />
              <text x={pad.l + i * bw + bw / 2} y={H - pad.b - h - 5} textAnchor="middle" className="axis">{b.count}</text>
              <text x={pad.l + i * bw + bw / 2} y={H - pad.b + 16} textAnchor="middle" className="axis">{b.label}</text>
            </g>
          );
        })}
        <text x={(pad.l + W - pad.r) / 2} y={H - 4} textAnchor="middle" className="axis">Delta (min)</text>
      </svg>
      <div className="legend small">
        <span><i style={{ background: "#2b6cb0" }} /> Over-estimated</span>
        <span><i style={{ background: "var(--ok)" }} /> ±15 min</span>
        <span><i style={{ background: "var(--warn)" }} /> 15–30 min</span>
        <span><i style={{ background: "var(--bad)" }} /> over 30 min</span>
      </div>
    </figure>
  );
}

const FILTERS = [
  { key: "all", label: "All", test: (_: CascadeRow) => true },
  { key: "15", label: "±15 min", test: (r: CascadeRow) => Math.abs(r.delta) <= 15 },
  { key: "30", label: "15–30 min", test: (r: CascadeRow) => Math.abs(r.delta) > 15 && Math.abs(r.delta) <= 30 },
  { key: "gt30", label: ">30 min", test: (r: CascadeRow) => Math.abs(r.delta) > 30 },
  { key: "over", label: "Overestimate", test: (r: CascadeRow) => r.delta < -15 },
];

function PairsTable({ rows, total }: { rows: CascadeRow[]; total: number }) {
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [showAll, setShowAll] = useState(false);
  const PAGE = 50;
  const shown = useMemo(() => {
    const test = FILTERS.find((f) => f.key === filter)?.test ?? (() => true);
    const q = query.trim().toLowerCase();
    return rows
      .filter(test)
      .filter((r) => !q || [r.flight, r.prev_flight, r.tail, r.route].some((v) => v.toLowerCase().includes(q)))
      .sort((a, b) => b.delta - a.delta);
  }, [rows, filter, query]);
  const visible = showAll ? shown : shown.slice(0, PAGE);
  return (
    <div className="cascade-table">
      <div className="cascade-table-head">
        <h3>All {num(total)} pairs</h3>
        <input type="search" aria-label="Search flight, tail or route" placeholder="Search flight, tail, route…" value={query} onChange={(e) => setQuery(e.target.value)} />
        <span className="chips" role="group" aria-label="Filter by delta">
          {FILTERS.map((f) => (
            <button key={f.key} type="button" aria-pressed={filter === f.key} className={filter === f.key ? "tab active" : "tab"} onClick={() => setFilter(f.key)}>
              {f.label}
            </button>
          ))}
        </span>
      </div>
      <div className="table-wrap">
        <table className="pax">
          <caption className="visually-hidden">Cascade pairs, largest delta first</caption>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Tail</th>
              <th scope="col">Prev flt</th>
              <th scope="col" className="num">Prev arr dly</th>
              <th scope="col">Flight</th>
              <th scope="col">Route</th>
              <th scope="col">STD</th>
              <th scope="col">Formula ETD</th>
              <th scope="col">Actual ATD</th>
              <th scope="col" className="num">Formula KO</th>
              <th scope="col" className="num">Actual KO</th>
              <th scope="col" className="num">Delta</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r, i) => (
              <tr key={`${r.date}-${r.flight}-${i}`}>
                <td>{r.date}</td>
                <td>{r.tail}</td>
                <td>{r.prev_flight}</td>
                <td className="num">{r.prev_arrival_delay}</td>
                <td><strong>{r.flight}</strong></td>
                <td>{r.route}</td>
                <td>{r.std}</td>
                <td>{r.formula_etd}</td>
                <td>{r.actual_atd}</td>
                <td className="num">{r.formula_ko}</td>
                <td className="num">{r.actual_ko}</td>
                <td className="num" style={{ color: BAND_COLOUR[band(r.delta)], fontWeight: 600 }}>{signed(r.delta)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {shown.length > PAGE && (
        <button type="button" className="link" onClick={() => setShowAll(!showAll)}>
          {showAll ? `Show the first ${PAGE} only` : `Show all ${num(shown.length)}`}
        </button>
      )}
      {shown.length === 0 && <p className="muted">No pairs match.</p>}
    </div>
  );
}
