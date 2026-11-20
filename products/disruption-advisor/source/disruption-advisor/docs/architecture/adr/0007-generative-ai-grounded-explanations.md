# ADR-0007: Generative AI only for grounded explanations and message drafts

- **Status:** Accepted (2026-11-20)
- **Context:** UC5 asks for explained recommendations and personalised communications. The data is treated as real passenger data (Q3), and the user allowed sending data to an external AI service. Decisions must stay explainable and auditable (GDPR Art. 22; human in the loop, Q21).
- **Decision:**
  - **Separation:** the engine decides. The Anthropic Claude API (Python SDK 2.12, model `claude-opus-5-5` per the Claude API guidance, `AI_MODEL` configurable, effort `low`) only rewrites the engine's facts into English text: the recommendation narrative and passenger message drafts.
  - **What is sent:** a fixed system instruction to use only the given facts. Facts exclude names, PNRs, contact details and customer keys.
  - **Resilience:** server-side refusal fallback (`fallbacks: "default"`). On any error, timeout (25 s) or refusal, deterministic templates are used, and the UI shows which source wrote each text.
- **Consequences:**
  - The product works with no API key.
  - About 4 s for an AI-worded scenario.
  - Explanation quality depends on the model, but the numbers shown in the tables come from the engine.
  - API cost per scenario is small (short prompts, low effort).
