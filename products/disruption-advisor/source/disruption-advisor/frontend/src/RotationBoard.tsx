import { useMemo, useRef, useState } from "react";
import type { Meta, OptionLeg, RecoveryOption } from "./api";
import { hhmm, minutes } from "./format";

/** Before/after Gantt of the aircraft a recovery option touches, in the style of an ops flight-watch board. */

interface Bar {
  leg: OptionLeg;
  tail: string;
  start: number;
  end: number;
  kind: "planned" | "disrupted" | "late" | "moved";
}

const SPANS = [
  { label: "24 h", hours: 24, pxPerHour: 64 },
  { label: "48 h", hours: 48, pxPerHour: 36 },
  { label: "7 days", hours: 168, pxPerHour: 12 },
] as const;
const AC_WIDTH = 120;

/** The API sends naive UTC timestamps ("2026-11-21T02:00:00"). */
const ms = (value: string): number => {
  const v = value.length === 16 ? `${value}:00` : value;
  return Date.parse(/(Z|[+-]\d\d:?\d\d)$/.test(v) ? v : `${v}Z`);
};

export function buildBars(option: RecoveryOption, disruptedId: string, after: boolean): Bar[] {
  return option.legs.map((leg) => {
    const block = ms(leg.new_sta) - ms(leg.new_std);
    if (!after) {
      const start = ms(leg.std);
      return { leg, tail: leg.scheduled_tail, start, end: start + block, kind: "planned" };
    }
    const kind = leg.flight_id === disruptedId ? "disrupted"
      : leg.operated_by !== leg.scheduled_tail ? "moved"
      : leg.delay_minutes > 0 ? "late" : "planned";
    return { leg, tail: leg.operated_by, start: ms(leg.new_std), end: ms(leg.new_sta), kind };
  });
}

export function RotationBoard({ option, disruptedId, meta }: { option: RecoveryOption; disruptedId: string; meta: Meta }) {
  const [spanIdx, setSpanIdx] = useState(0);
  const span = SPANS[spanIdx] ?? SPANS[0];
  const before = useMemo(() => buildBars(option, disruptedId, false), [option, disruptedId]);
  const after = useMemo(() => buildBars(option, disruptedId, true), [option, disruptedId]);
  const disruptedTail = option.legs.find((l) => l.flight_id === disruptedId)?.scheduled_tail;
  const tails = useMemo(() => {
    const set = new Set<string>([...before, ...after].map((b) => b.tail));
    return [...set].sort((a, b) => (a === disruptedTail ? -1 : b === disruptedTail ? 1 : a.localeCompare(b)));
  }, [before, after, disruptedTail]);
  const t0 = Math.floor((Math.min(...before.map((b) => b.start).filter(Number.isFinite)) - 3600e3) / 3600e3) * 3600e3;
  const t1 = t0 + span.hours * 3600e3;
  const width = AC_WIDTH + span.hours * span.pxPerHour;
  const moved = option.legs.filter((l) => l.operated_by !== l.scheduled_tail).length;
  const late = option.legs.filter((l) => l.delay_minutes > 0).length;
  const turnAt = (station: string) =>
    meta.min_turn_minutes?.by_station[station] ?? meta.min_turn_minutes?.default ?? 0;

  const beforeRef = useRef<HTMLDivElement>(null);
  const afterRef = useRef<HTMLDivElement>(null);
  const boards = [beforeRef, afterRef] as const;
  const sync = (from: 0 | 1) => () => {
    const a = boards[from].current, b = boards[from === 0 ? 1 : 0].current;
    if (a && b && b.scrollLeft !== a.scrollLeft) b.scrollLeft = a.scrollLeft;
  };

  const starts = before.map((b) => b.start).filter(Number.isFinite);
  if (!starts.length) return null;

  const board = (bars: Bar[], idx: 0 | 1, title: string, tag: string) => (
    <div className="rb-block">
      <div className="rb-title"><span className={`rb-tag ${tag}`}>{tag === "before" ? "Before" : "After"}</span>{title}</div>
      <div className="rb-board" ref={boards[idx]} onScroll={sync(idx)} role="region" aria-label={`${title} rotation`} tabIndex={0}>
        <div className="rb-grid" style={{ width }}>
          <div className="rb-hdr">
            <div className="rb-ac">UTC</div>
            {Array.from({ length: span.hours + 1 }, (_, h) => {
              const t = t0 + h * 3600e3, d = new Date(t), hour = d.getUTCHours();
              const every = span.hours > 48 ? 6 : span.hours > 24 ? 2 : 1;
              return (
                <div key={h}>
                  {(h === 0 || hour === 0) && (
                    <span className="rb-date" style={{ left: AC_WIDTH + h * span.pxPerHour }}>
                      {d.toISOString().slice(8, 10)}/{d.toISOString().slice(5, 7)}
                    </span>
                  )}
                  {h > 0 && h < span.hours && hour % every === 0 && (
                    <span className="rb-hour" style={{ left: AC_WIDTH + h * span.pxPerHour }}>
                      {String(hour).padStart(2, "0")}:00
                    </span>
                  )}
                </div>
              );
            })}
          </div>
          {tails.map((tail) => {
            const row = bars.filter((b) => b.tail === tail).sort((a, b) => a.start - b.start);
            const x = (t: number) => AC_WIDTH + ((t - t0) / 3600e3) * span.pxPerHour;
            return (
              <div className="rb-row" key={tail}>
                <div className={`rb-ac ${tail === disruptedTail ? "hit" : ""}`}>{tail}</div>
                {row.map((b, i) => {
                  const next = row[i + 1];
                  if (!next || next.start <= b.end || b.leg.destination !== next.leg.origin) return null;
                  const L = Math.max(x(b.end), AC_WIDTH), R = Math.min(x(next.start), width);
                  if (R - L < 24 || b.end > t1) return null;
                  const gap = Math.round((next.start - b.end) / 60e3);
                  const short = gap < turnAt(b.leg.destination);
                  return (
                    <div key={`g${b.leg.flight_id}`} className={`rb-gnd ${short ? "short" : ""}`} style={{ left: L, width: R - L }}
                      title={`On the ground at ${b.leg.destination}: ${minutes(gap)} (minimum ${turnAt(b.leg.destination)} min)`}>
                      <span>{b.leg.destination}</span><span>{gap}′</span>
                    </div>
                  );
                })}
                {row.filter((b) => b.end > t0 && b.start < t1).map((b) => {
                  const L = Math.max(x(b.start), AC_WIDTH), w = Math.max(Math.min(x(b.end), width) - L, 4);
                  const from = b.kind === "moved" ? ` · taken over from ${b.leg.scheduled_tail}` : "";
                  const delay = idx === 1 && b.leg.delay_minutes > 0 ? ` · +${minutes(b.leg.delay_minutes)}` : "";
                  return (
                    <div key={b.leg.flight_id} className={`rb-bar ${b.kind}`} style={{ left: L, width: w }}
                      title={`${b.leg.flight_number} ${b.leg.origin}-${b.leg.destination} ${hhmm(new Date(b.start).toISOString())}–${hhmm(new Date(b.end).toISOString())}Z · ${b.leg.booked_pax} booked${from}${delay}`}>
                      {idx === 1 && b.leg.delay_minutes > 0 && <span className="rb-badge">{b.leg.delay_minutes}</span>}
                      <span className="rb-fn">{b.leg.flight_number}</span>
                      <span className="rb-rt">{b.leg.origin} - {b.leg.destination}</span>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );

  return (
    <section aria-labelledby="rotation-title" className="rb">
      <div className="rb-head">
        <h2 id="rotation-title">How the aircraft change: {option.label}</h2>
        <label className="small">
          Show{" "}
          <select value={spanIdx} onChange={(e) => setSpanIdx(Number(e.target.value))} aria-label="Time span">
            {SPANS.map((s, i) => <option key={s.label} value={i}>{s.label}</option>)}
          </select>
        </label>
      </div>
      <p className="small muted">
        {late} flight(s) leave late and {moved} flight(s) move to another aircraft. Same aircraft and time axis in both
        boards (UTC); scroll one and the other follows. Ground time in red is below the minimum turn.
      </p>
      <div className="rb-legend small">
        <span><i className="rb-sw planned" />Planned</span>
        <span><i className="rb-sw disrupted" />Disrupted flight</span>
        <span><i className="rb-sw late" />Leaves late</span>
        <span><i className="rb-sw moved" />Taken over by this aircraft</span>
      </div>
      {board(before, 0, "Rotation as planned", "before")}
      {board(after, 1, "With this option", "after")}
    </section>
  );
}
