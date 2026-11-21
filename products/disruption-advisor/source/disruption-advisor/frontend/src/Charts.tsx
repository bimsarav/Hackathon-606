import { useState } from "react";

/* Small SVG charts for the Model Card (dataviz skill: thin marks, 4px rounded data-ends, 2px lines, 8px markers with a
   2px surface ring, recessive grid, legend for 2+ series, a hover tooltip on every mark). Colours: --series-1/--series-2,
   validated light and dark (validate_palette.js, both modes PASS). Every chart sits next to a table with the same numbers. */

export interface Series {
  name: string;
  values: (number | null)[];
}

const W = 560;
const H = 240;
const PAD = { top: 16, right: 16, bottom: 44, left: 52 };
const COLORS = ["var(--series-1)", "var(--series-2)"];

function ticks(min: number, max: number, count = 4): number[] {
  const step = (max - min) / count;
  return Array.from({ length: count + 1 }, (_, i) => min + i * step);
}

function Legend({ series }: { series: Series[] }) {
  if (series.length < 2) return null;
  return (
    <ul className="chart-legend">
      {series.map((s, i) => (
        <li key={s.name}>
          <span className="chart-swatch" style={{ background: COLORS[i % COLORS.length] }} aria-hidden="true" />
          {s.name}
        </li>
      ))}
    </ul>
  );
}

function Tip({ x, y, lines }: { x: number; y: number; lines: string[] }) {
  const width = Math.max(...lines.map((l) => l.length)) * 6.6 + 16;
  const height = lines.length * 16 + 10;
  const left = Math.min(Math.max(x - width / 2, 2), W - width - 2);
  const top = Math.max(y - height - 10, 2);
  return (
    <g className="chart-tip" pointerEvents="none">
      <rect x={left} y={top} width={width} height={height} rx={6} />
      {lines.map((l, i) => (
        <text key={i} x={left + 8} y={top + 18 + i * 16} className={i === 0 ? "chart-tip-head" : undefined}>{l}</text>
      ))}
    </g>
  );
}

function Frame({ title, children, series, caption }: { title: string; children: React.ReactNode; series: Series[]; caption?: string }) {
  return (
    <figure className="chart">
      <figcaption className="chart-title">{title}</figcaption>
      <Legend series={series} />
      {children}
      {caption && <p className="chart-caption small muted">{caption}</p>}
    </figure>
  );
}

function YAxis({ min, max, y, format }: { min: number; max: number; y: (v: number) => number; format: (v: number) => string }) {
  return (
    <g className="chart-axis">
      {ticks(min, max).map((t) => (
        <g key={t}>
          <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} className="chart-grid" />
          <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end">{format(t)}</text>
        </g>
      ))}
    </g>
  );
}

/** Vertical grouped bars from one baseline. */
export function BarChart({ title, categories, series, format, min = 0, max, caption }: {
  title: string; categories: string[]; series: Series[]; format: (v: number) => string; min?: number; max?: number; caption?: string;
}) {
  const [hover, setHover] = useState<{ c: number; s: number } | null>(null);
  const all = series.flatMap((s) => s.values.filter((v): v is number => v != null));
  const top = max ?? Math.max(...all, min + 1e-9) * 1.1;
  const y = (v: number) => PAD.top + (1 - (v - min) / (top - min)) * (H - PAD.top - PAD.bottom);
  const band = (W - PAD.left - PAD.right) / categories.length;
  const bar = Math.min(24, (band * 0.7 - (series.length - 1) * 2) / series.length);
  const group = bar * series.length + (series.length - 1) * 2;
  const base = y(min);
  return (
    <Frame title={title} series={series} caption={caption}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title} className="chart-svg">
        <YAxis min={min} max={top} y={y} format={format} />
        {categories.map((c, ci) => {
          const x0 = PAD.left + ci * band + (band - group) / 2;
          return (
            <g key={c}>
              {series.map((s, si) => {
                const v = s.values[ci];
                if (v == null) return null;
                const x = x0 + si * (bar + 2);
                const top = Math.min(y(v), base - 1);
                const r = Math.min(4, (base - top) / 2, bar / 2);
                const d = `M${x},${base} V${top + r} Q${x},${top} ${x + r},${top} H${x + bar - r} Q${x + bar},${top} ${x + bar},${top + r} V${base} Z`;
                const on = hover?.c === ci && hover.s === si;
                return (
                  <path key={s.name} d={d} fill={COLORS[si % COLORS.length]} opacity={hover && !on ? 0.55 : 1}
                    onMouseEnter={() => setHover({ c: ci, s: si })} onMouseLeave={() => setHover(null)}>
                    <title>{`${c} · ${s.name}: ${format(v)}`}</title>
                  </path>
                );
              })}
              <text x={PAD.left + ci * band + band / 2} y={H - PAD.bottom + 16} textAnchor="middle" className="chart-label">{c}</text>
            </g>
          );
        })}
        <line x1={PAD.left} x2={W - PAD.right} y1={base} y2={base} className="chart-baseline" />
        {hover && series[hover.s] && series[hover.s]!.values[hover.c] != null && (
          <Tip x={PAD.left + hover.c * band + band / 2} y={y(series[hover.s]!.values[hover.c] as number)}
            lines={[categories[hover.c] ?? "", ...series.map((s) => `${s.name}: ${s.values[hover.c] == null ? "—" : format(s.values[hover.c] as number)}`)]} />
        )}
      </svg>
    </Frame>
  );
}

/** Lines over ordered categories, with a crosshair tooltip per category. */
export function LineChart({ title, categories, series, format, min, max, xLabel, caption }: {
  title: string; categories: string[]; series: Series[]; format: (v: number) => string; min?: number; max?: number; xLabel?: string; caption?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const all = series.flatMap((s) => s.values.filter((v): v is number => v != null));
  const lo = min ?? Math.min(...all);
  const hi = max ?? Math.max(...all);
  const span = hi - lo || 1;
  const y = (v: number) => PAD.top + (1 - (v - lo) / span) * (H - PAD.top - PAD.bottom);
  const step = categories.length > 1 ? (W - PAD.left - PAD.right) / (categories.length - 1) : 0;
  const x = (i: number) => PAD.left + i * step;
  const every = Math.ceil(categories.length / 8);
  return (
    <Frame title={title} series={series} caption={caption}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title} className="chart-svg" onMouseLeave={() => setHover(null)}>
        <YAxis min={lo} max={hi} y={y} format={format} />
        {categories.map((c, i) => (i % every === 0 ? (
          <text key={c} x={x(i)} y={H - PAD.bottom + 16} textAnchor="middle" className="chart-label">{c}</text>
        ) : null))}
        {xLabel && <text x={(W + PAD.left) / 2} y={H - 6} textAnchor="middle" className="chart-label">{xLabel}</text>}
        {hover != null && <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={H - PAD.bottom} className="chart-crosshair" />}
        {series.map((s, si) => {
          const pts = s.values.map((v, i) => (v == null ? null : `${x(i)},${y(v)}`)).filter(Boolean).join(" L");
          return (
            <g key={s.name}>
              <path d={`M${pts}`} fill="none" stroke={COLORS[si % COLORS.length]} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
              {s.values.map((v, i) => (v == null || (hover !== i && categories.length > 12) ? null : (
                <circle key={i} cx={x(i)} cy={y(v)} r={4} fill={COLORS[si % COLORS.length]} className="chart-dot" />
              )))}
            </g>
          );
        })}
        {categories.map((c, i) => (
          <rect key={c} x={x(i) - step / 2} y={PAD.top} width={Math.max(step, 8)} height={H - PAD.top - PAD.bottom}
            fill="transparent" onMouseEnter={() => setHover(i)} />
        ))}
        {hover != null && (
          <Tip x={x(hover)} y={Math.min(...series.map((s) => (s.values[hover] == null ? H : y(s.values[hover] as number))))}
            lines={[categories[hover] ?? "", ...series.map((s) => `${s.name}: ${s.values[hover] == null ? "—" : format(s.values[hover] as number)}`)]} />
        )}
      </svg>
    </Frame>
  );
}

/** Predicted chance (x) against what happened (y), with the perfect-calibration diagonal. */
export function CalibrationChart({ title, bins, caption }: {
  title: string; bins: { from: number; to: number; flights: number; predicted: number; observed: number }[]; caption?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const top = Math.min(1, Math.max(0.1, ...bins.flatMap((b) => [b.predicted, b.observed])) * 1.15);
  const sx = (v: number) => PAD.left + (v / top) * (W - PAD.left - PAD.right);
  const sy = (v: number) => PAD.top + (1 - v / top) * (H - PAD.top - PAD.bottom);
  const pc = (v: number) => `${Math.round(v * 100)}%`;
  return (
    <Frame title={title} series={[]} caption={caption ?? "Dots on the dashed line mean the stated chance came true that often."}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title} className="chart-svg">
        <YAxis min={0} max={top} y={sy} format={pc} />
        {ticks(0, top).map((t) => (
          <text key={t} x={sx(t)} y={H - PAD.bottom + 16} textAnchor="middle" className="chart-label">{pc(t)}</text>
        ))}
        <text x={(W + PAD.left) / 2} y={H - 6} textAnchor="middle" className="chart-label">predicted chance</text>
        <line x1={sx(0)} y1={sy(0)} x2={sx(top)} y2={sy(top)} className="chart-reference" />
        {bins.map((b, i) => (
          <circle key={b.from} cx={sx(b.predicted)} cy={sy(b.observed)} r={hover === i ? 6 : 5} fill="var(--series-1)" className="chart-dot"
            onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
            <title>{`${pc(b.from)}–${pc(b.to)}: predicted ${pc(b.predicted)}, happened ${pc(b.observed)} (${b.flights})`}</title>
          </circle>
        ))}
        {hover != null && bins[hover] && (
          <Tip x={sx(bins[hover]!.predicted)} y={sy(bins[hover]!.observed)}
            lines={[`${pc(bins[hover]!.from)} to ${pc(bins[hover]!.to)}`, `predicted ${pc(bins[hover]!.predicted)}`, `happened ${pc(bins[hover]!.observed)}`, `${bins[hover]!.flights} cases`]} />
        )}
      </svg>
    </Frame>
  );
}

/** Horizontal bars from zero, one row per item (long names, values that can be negative); value written at the bar end. */
export function HBarChart({ title, items, format, caption, highlight }: {
  title: string; items: { label: string; value: number | null }[]; format: (v: number) => string; caption?: string; highlight?: (label: string) => boolean;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const rows = items.filter((i): i is { label: string; value: number } => i.value != null);
  const lo = Math.min(0, ...rows.map((r) => r.value));
  const hi = Math.max(0, ...rows.map((r) => r.value));
  const left = 190;
  const right = 70;
  const rowH = 26;
  const height = rows.length * rowH + 16;
  const x = (v: number) => left + ((v - lo) / (hi - lo || 1)) * (W - left - right);
  const zero = x(0);
  return (
    <Frame title={title} series={[]} caption={caption}>
      <svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label={title} className="chart-svg">
        {rows.map((r, i) => {
          const y = 8 + i * rowH;
          const a = Math.min(zero, x(r.value));
          const w = Math.max(Math.abs(x(r.value) - zero), 1);
          const strong = highlight?.(r.label) ?? false;
          return (
            <g key={r.label} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
              <text x={left - 8} y={y + 15} textAnchor="end" className="chart-label" fontWeight={strong ? 600 : undefined}>
                {r.label.length > 30 ? `${r.label.slice(0, 29)}…` : r.label}
              </text>
              <rect x={a} y={y + 4} width={w} height={14} rx={4} fill="var(--series-1)" opacity={hover != null && hover !== i ? 0.55 : strong || !highlight ? 1 : 0.7}>
                <title>{`${r.label}: ${format(r.value)}`}</title>
              </rect>
              <text x={r.value < 0 ? zero + 6 : a + w + 6} y={y + 15} textAnchor="start" className="chart-label">{format(r.value)}</text>
            </g>
          );
        })}
        <line x1={zero} x2={zero} y1={4} y2={height - 4} className="chart-baseline" />
      </svg>
    </Frame>
  );
}
