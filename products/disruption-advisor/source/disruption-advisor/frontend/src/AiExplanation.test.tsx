import { render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Scenario } from "./api";
import { Explanation, useAiExplanation, whyLabel } from "./Shared";

function Page({ start }: { start: Scenario }) {
  const [s, setS] = useState(start);
  useAiExplanation(s, setS);
  const e = s.result.explanation;
  return <><span>{whyLabel(e.source, e.pending)}</span><Explanation text={e.text} source={e.source} pending={e.pending} /></>;
}

afterEach(() => vi.unstubAllGlobals());

describe("the AI wording arrives after the analysis", () => {
  it("shows the template at once, then swaps in the AI text", async () => {
    const fetchFn = vi.fn(async () => new Response(JSON.stringify({ text: "AI says why.", source: "ai:claude-opus-5-5", pending: false }), { status: 200 }));
    vi.stubGlobal("fetch", fetchFn);
    const scenario = { id: "s1", result: { explanation: { text: "Template says why.", source: "template", pending: true } } } as unknown as Scenario;
    render(<Page start={scenario} />);
    expect(screen.getByText("Template says why.")).toBeInTheDocument();
    expect(screen.getByText("Writing…")).toBeInTheDocument();
    expect(await screen.findByText("AI says why.")).toBeInTheDocument();
    expect(screen.getByText("AI-worded")).toBeInTheDocument();
    expect(fetchFn).toHaveBeenCalledTimes(1);
  });
});
