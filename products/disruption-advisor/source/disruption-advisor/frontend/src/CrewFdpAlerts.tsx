import type { RecoveryOption } from "./api";
import { minutes, num, utc } from "./format";

const CREW_TYPE: Record<string, string> = {
  CP: "Captain", FO: "First officer", SO: "Second officer", CS: "Senior cabin crew", CC: "Cabin crew",
};

/** Crew FDPs: an alert, shown only when a recovery option would take a crew past its maximum
 *  flight duty period. Alert only at this stage: no crew recovery is planned. */
export function CrewFdpAlerts({ options, selectedKey }: { options: RecoveryOption[]; selectedKey: string }) {
  const breaching = options.filter((o) => o.crew?.status === "over");
  if (breaching.length === 0) return null;
  // the selected option first, then the rest in the table's order
  const ordered = [...breaching].sort((a, b) => Number(b.key === selectedKey) - Number(a.key === selectedKey));
  const selectedBreaches = breaching.some((o) => o.key === selectedKey);

  return (
    <section className="crew-fdps" aria-labelledby="crew-fdps-title">
      <h2 id="crew-fdps-title">Crew FDPs</h2>
      <p role="alert" className={selectedBreaches ? "crew-fdp-alert bad" : "crew-fdp-alert"}>
        <strong>FDP breach:</strong>{" "}
        {selectedBreaches
          ? "the selected option would take a crew past its maximum flight duty period."
          : `${num(breaching.length)} of ${num(options.length)} options would take a crew past its maximum flight duty period; the selected option does not.`}
      </p>
      <div className="table-wrap">
        <table>
          <caption className="visually-hidden">Flights whose crew would pass the maximum FDP, by option</caption>
          <thead>
            <tr>
              <th scope="col">Option</th>
              <th scope="col">Flight</th>
              <th scope="col">New departure</th>
              <th scope="col">Crew</th>
              <th scope="col" className="num">Delay</th>
              <th scope="col" className="num">FDP headroom</th>
              <th scope="col" className="num">Breach</th>
            </tr>
          </thead>
          <tbody>
            {ordered.flatMap((o) =>
              (o.crew?.flights ?? []).filter((f) => f.status === "over").map((f, i) => (
                <tr key={`${o.key}:${f.flight_id}`} className={o.key === selectedKey ? "selected" : ""}>
                  <td>
                    {i === 0 && (
                      <>
                        {o.label}
                        {o.key === selectedKey && <span className="chip small">Selected</span>}
                      </>
                    )}
                  </td>
                  <th scope="row">
                    {f.flight_number}
                    {f.origin && <span className="muted"> {f.origin}→{f.destination}</span>}
                  </th>
                  <td>{f.new_std ? utc(f.new_std) : "—"}</td>
                  <td>
                    {f.crew_type ? CREW_TYPE[f.crew_type] ?? f.crew_type : "Crew"}
                    <span className="small muted block">
                      {f.source === "estimated" ? "estimated from the flight's history" : "from the crew roster"}
                    </span>
                  </td>
                  <td className="num">{minutes(f.delay_minutes)}</td>
                  <td className="num">{minutes(f.headroom_minutes)}</td>
                  <td className="num"><span className="chip small chip-bad">{minutes(-f.minutes_left)} over</span></td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>
      <p className="small muted">
        Headroom = maximum FDP − planned FDP of the tightest crew member on the flight. Crews are assumed to stay with
        their flight. For crew control to review; no crew recovery is planned here.
      </p>
    </section>
  );
}
