import { useCallback, useEffect, useState } from "react";
import { FlightEditor } from "./FlightEditor";
import {
  api,
  errorText,
  type TestDataFile,
  type TestDataReport,
  type TestDataSpec,
  type TestDataStatus,
} from "./api";

type Keys = TestDataFile["key"];

function readText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(new Error("The file could not be read."));
    reader.readAsText(file);
  });
}

function download(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

/** Judge / evaluator test data: a few flights and their passengers, added on top of the real data. */
export function TestDataPanel() {
  const [spec, setSpec] = useState<TestDataSpec | null>(null);
  const [status, setStatus] = useState<TestDataStatus | null>(null);
  const [files, setFiles] = useState<Partial<Record<Keys, { name: string; text: string }>>>({});
  const [report, setReport] = useState<TestDataReport | null>(null);
  const [checked, setChecked] = useState(false); // the files on screen passed the check
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.testDataSpec().then(setSpec).catch((e) => setError(errorText(e, "Could not load the file description.")));
    api.testData().then(setStatus).catch((e) => setError(errorText(e, "Could not load the test data status.")));
  }, []);

  const choose = useCallback(async (key: Keys, file: File | undefined) => {
    setReport(null);
    setChecked(false);
    if (!file) {
      setFiles((f) => ({ ...f, [key]: undefined }));
      return;
    }
    try {
      const text = await readText(file);
      setFiles((f) => ({ ...f, [key]: { name: file.name, text } }));
    } catch (e) {
      setError(errorText(e, "The file could not be read."));
    }
  }, []);

  const send = async (commit: boolean) => {
    if (!files.flights || !files.passengers) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.uploadTestData(files.flights.text, files.passengers.text, commit);
      setReport(result);
      setChecked(result.ok);
      if (result.committed && result.status) {
        setStatus(result.status);
        setChecked(false);
      }
    } catch (e) {
      setError(errorText(e, "The upload failed."));
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    setError(null);
    try {
      setStatus(await api.removeTestData());
      setReport(null);
    } catch (e) {
      setError(errorText(e, "The test data could not be removed."));
    } finally {
      setBusy(false);
    }
  };

  const ready = Boolean(files.flights && files.passengers);

  return (
    <section className="testdata" aria-label="Test data">
      <h2>Test data</h2>
      <p className="muted small">
        Add a few flights and their passengers to try the advisor on your own cases. They are added to the live
        data and labelled <strong>judge test data</strong>; the real data and the trained models stay unchanged.
        After adding, search the flight in the <strong>Scenario</strong> tab, set a delay or a cancellation and
        review the disruption, rebooking and rewards.
      </p>
      {error && <p className="error" role="alert">{error}</p>}

      {status?.loaded && (
        <div className="testdata-status" role="status">
          <p>
            <span className="chip chip-synthetic">Test data loaded</span>{" "}
            {status.counts?.flights} flights, {status.counts?.passengers} passengers
            {status.uploaded_by ? `, added by ${status.uploaded_by}` : ""}
            {status.uploaded_at ? ` on ${status.uploaded_at.replace("T", " ").replace("+00:00", " UTC")}` : ""}.
          </p>
          {status.risk && (
            <p className="small">
              {status.risk.scored > 0
                ? `Delay risk scored with the saved model for ${status.risk.scored} flights and ${status.risk.connections} connections: they appear in the 7-day watchlist.`
                : `Delay risk was not scored (${status.risk.reason ?? "unknown reason"}), so the flights are not in the 7-day watchlist.`}
            </p>
          )}
          <table className="pax" aria-label="Test flights">
            <thead>
              <tr><th>Flight</th><th>Route</th><th>Departs (UTC)</th><th>Aircraft</th><th>Passengers listed</th><th>Seats sold / capacity</th></tr>
            </thead>
            <tbody>
              {status.flights?.map((f) => (
                <tr key={f.flight_id}>
                  <td>{f.flight_number}</td><td>{f.route}</td><td>{f.std}</td><td>{f.tail}</td>
                  <td>{f.passengers}</td><td>{f.booked_seats} / {f.capacity}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <button type="button" className="reject" disabled={busy} onClick={remove}>Remove test data</button>
        </div>
      )}
      {status && !status.loaded && <p className="muted small">No test data is loaded; the advisor shows the real data only.</p>}

      {spec && (
        <>
          <p className="small">
            <strong>Format:</strong> {spec.format} Up to {spec.limits.flights} flights and {spec.limits.passenger_rows} passenger rows.
          </p>
          <div className="testdata-files">
            {spec.files.map((file) => (
              <article key={file.key} className="testdata-file" aria-label={file.title}>
                <h3>{file.title}</h3>
                <p className="small">{file.purpose}</p>
                <table className="pax" aria-label={`${file.title} columns`}>
                  <thead>
                    <tr><th>Column</th><th>Needed</th><th>Example</th><th>Meaning</th></tr>
                  </thead>
                  <tbody>
                    {file.fields.map((f) => (
                      <tr key={f.name}>
                        <td><code>{f.name}</code></td>
                        <td>{f.required ? "yes" : "optional"}</td>
                        <td>{f.example || "—"}</td>
                        <td>{f.help}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="testdata-actions">
                  <button type="button" className="link" onClick={() => download(file.file_name, file.template)}>
                    Download template ({file.file_name})
                  </button>
                  <label>
                    Choose {file.title.toLowerCase()}{" "}
                    <input
                      type="file"
                      accept=".csv,text/csv"
                      aria-label={`Upload ${file.title.toLowerCase()}`}
                      onChange={(e) => void choose(file.key, e.target.files?.[0])}
                    />
                  </label>
                  {files[file.key] && <span className="small muted">{files[file.key]?.name}</span>}
                </div>
              </article>
            ))}
          </div>
          <div className="testdata-actions">
            <button type="button" disabled={!ready || busy} onClick={() => void send(false)}>Check files</button>
            <button type="button" className="primary" disabled={!ready || !checked || busy} onClick={() => void send(true)}>
              Add to system
            </button>
            {!ready && <span className="small muted">Choose both files first.</span>}
            {ready && !checked && !report && <span className="small muted">Check the files, then add them.</span>}
            {status?.loaded && checked && (
              <span className="small muted">Adding replaces the test data that is loaded now.</span>
            )}
          </div>
        </>
      )}

      {report && (
        <div className="testdata-report" role="status" aria-live="polite">
          {report.ok ? (
            <p>
              <span className="chip chip-ok">{report.committed ? "Added" : "Files are valid"}</span>{" "}
              {report.summary.flights} flights, {report.summary.passengers} passengers,{" "}
              {report.summary.passenger_segments} passenger-flight rows.
              {report.committed
                ? " Search the flight in the Scenario tab."
                : " Press “Add to system” to load them."}
            </p>
          ) : (
            <>
              <p><span className="chip chip-bad">Not added</span> Fix these problems and check again. Nothing was changed.</p>
              <table className="pax" aria-label="Problems found">
                <thead><tr><th>File</th><th>Row</th><th>Column</th><th>Problem</th></tr></thead>
                <tbody>
                  {report.errors.map((e, i) => (
                    <tr key={i}>
                      <td>{e.file}</td><td>{e.row ?? "—"}</td><td>{e.column ?? "—"}</td><td>{e.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
          {report.warnings.length > 0 && (
            <ul className="small">
              {report.warnings.map((w) => <li key={w}>{w}</li>)}
            </ul>
          )}
        </div>
      )}

      {spec && (
        <ul className="small muted">
          {spec.notes.map((n) => <li key={n}>{n}</li>)}
        </ul>
      )}

      <FlightEditor />
    </section>
  );
}
