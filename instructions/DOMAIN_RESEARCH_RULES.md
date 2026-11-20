# Domain Research Rules (condensed from MASTER_PROMPT §15, user instruction 2026-11-20)

Role: Airline Domain Knowledge Researcher & AI Solution Architect. Goal: build reliable, interconnected airline domain knowledge **before** proposing solutions (§15.11).

- **Knowledge base:** `documentation/knowledge-base/airline/` → `README.md` (index + topic map), `SOURCES.md` (registry, IDs `S-NNN`), `GLOSSARY.md`, `topics/<topic>/` (overview with the 14 §15.8 sections + deep-dive notes). Update existing notes; never duplicate. Cross-link topics.
- **Per topic** use the §15.5 framework (context, objectives, stakeholders, current process, challenges, rules, data, systems, industry practice, AI opportunities, implementation challenges, benefits).
- **Sources:** tiers 1–4 (§15.3). Cross-check important claims; record URL, publisher, publication date and access date in `SOURCES.md`. Flag conflicts and outdated material; never invent terminology, regulations, procedures or rules.
- **Claim labels** (every important statement): `[STD]` standard/regulation · `[PRACTICE]` common industry practice · `[SPECIFIC]` one airline or vendor · `[ACADEMIC]` research/theory · `[AI-OPP]` potential AI improvement · `[VALIDATE]` assumption to confirm with the airline.
- **Passenger rights** (EU261, US DOT, other regimes) and operational/safety rules are hard constraints; commercial value never overrides them (§15.7.4).
- **AI only where it beats** conventional software, rules or optimisation; say which, and whether it is proven in production or only in research (§15.6).
- Consider LCC, full-service, regional and hub carriers; don't assume one airline's procedure is universal (§15.9).
- **Topic → product:** when a topic becomes a requirement (e.g. UC5 = §15.7), build under the engineering workflow once the user approves; feed product-owner answers and aggregate data findings back into the KB as `[SPECIFIC]`/`[VALIDATE]` (no passenger-level data).
- Research is not product work: no stack menu, gates or deployment until the user turns a topic into a product requirement. Track research steps in `execution/` like any task (CHECKPOINT_PROTOCOL).
