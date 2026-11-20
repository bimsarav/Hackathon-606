import { type FormEvent, useEffect, useState } from "react";
import { ApiError, createNote, listNotes, type Note } from "./api";

type LoadState = { kind: "loading" } | { kind: "error"; message: string } | { kind: "ready"; notes: Note[] };

/** Example screen with loading, empty, error and success states. Replace with the product's own UI. */
export function App() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    listNotes()
      .then((page) => setState({ kind: "ready", notes: page.items }))
      .catch((error: unknown) =>
        setState({ kind: "error", message: error instanceof Error ? error.message : "Could not load notes" }),
      );
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      const note = await createNote(title, body);
      setState((current) => (current.kind === "ready" ? { kind: "ready", notes: [note, ...current.notes] } : current));
      setTitle("");
      setBody("");
    } catch (error: unknown) {
      setFormError(error instanceof ApiError ? (error.problem.errors?.[0]?.msg ?? error.message) : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="site-header">
        <span className="brand">Sample App</span>
        <a href="/api/docs">API documentation</a>
      </header>
      <main id="main">
        <h1>Notes</h1>
        <form onSubmit={onSubmit} aria-describedby={formError ? "form-error" : undefined}>
          <label htmlFor="title">Title</label>
          <input id="title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} required />
          <label htmlFor="body">Body</label>
          <textarea id="body" value={body} onChange={(e) => setBody(e.target.value)} rows={3} />
          {formError && (
            <p id="form-error" className="error" role="alert">
              {formError}
            </p>
          )}
          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Add note"}
          </button>
        </form>
        <section aria-live="polite" aria-busy={state.kind === "loading"}>
          {state.kind === "loading" && <p>Loading notes…</p>}
          {state.kind === "error" && (
            <p className="error" role="alert">
              {state.message}
            </p>
          )}
          {state.kind === "ready" && state.notes.length === 0 && <p>No notes yet.</p>}
          {state.kind === "ready" && state.notes.length > 0 && (
            <ul className="notes">
              {state.notes.map((note) => (
                <li key={note.id}>
                  <strong>{note.title}</strong> {note.body && <span>{note.body}</span>}
                  <time dateTime={note.created_at}>{new Date(note.created_at).toLocaleString()}</time>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </>
  );
}
