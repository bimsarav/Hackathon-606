import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const note = { id: 1, title: "first", body: "hello", created_at: "2026-11-20T10:00:00Z" };

function mockFetch(...responses: { status: number; body: unknown }[]) {
  const fetchMock = vi.fn();
  for (const { status, body } of responses) {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(body), { status }));
  }
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe("App", () => {
  it("shows the empty state", async () => {
    mockFetch({ status: 200, body: { items: [], limit: 50, offset: 0 } });
    render(<App />);
    expect(await screen.findByText("No notes yet.")).toBeInTheDocument();
  });

  it("lists notes", async () => {
    mockFetch({ status: 200, body: { items: [note], limit: 50, offset: 0 } });
    render(<App />);
    expect(await screen.findByText("first")).toBeInTheDocument();
  });

  it("shows a load error", async () => {
    mockFetch({ status: 500, body: { title: "Internal Server Error", status: 500 } });
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Internal Server Error");
  });

  it("creates a note", async () => {
    const fetchMock = mockFetch(
      { status: 200, body: { items: [], limit: 50, offset: 0 } },
      { status: 201, body: { ...note, title: "new" } },
    );
    render(<App />);
    await screen.findByText("No notes yet.");
    await userEvent.type(screen.getByLabelText("Title"), "new");
    await userEvent.click(screen.getByRole("button", { name: "Add note" }));
    expect(await screen.findByText("new")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith("/api/v1/notes", expect.objectContaining({ method: "POST" }));
  });

  it("shows validation errors from problem details", async () => {
    mockFetch(
      { status: 200, body: { items: [], limit: 50, offset: 0 } },
      { status: 422, body: { title: "Unprocessable Content", status: 422, errors: [{ loc: ["body", "title"], msg: "too short" }] } },
    );
    render(<App />);
    await screen.findByText("No notes yet.");
    await userEvent.type(screen.getByLabelText("Title"), "x");
    await userEvent.click(screen.getByRole("button", { name: "Add note" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("too short");
  });
});
