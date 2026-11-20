# Tech Stack Standards (condensed)

Source: user instructions of 2026-11-20. The full text is `MASTER_PROMPT.md` §9; "standards §N" anywhere in this workspace means master prompt §9.N.
Scope (user decision D-005): applies to every **new** product. esm-hub keeps the stack in `PRODUCT_RULES.md` §3 and carries the §9.16 documents.
Product path mapping: `documentation/` = the product repo's `docs/`; `ARCHITECTURE_DECISIONS/` = `docs/architecture/adr/`; for esm-hub, `SYSTEM_ARCHITECTURE.md` = `docs/architecture/architecture.md` (new products use the standard name).

- Choose the stack for the problem domain (§9.1, §9.17). Python, PHP, Java, JS/TS and .NET are equal candidates; never adopt the whole catalogue.
- Prefer mature, supported, **LTS** versions. Prefer the simplest architecture: no microservices, Kubernetes, brokers, extra databases or AI/ML without a requirement (§9.2, §9.19).
- **Selection checkpoint, early Phase 2** (§4, §9.16): finish the domain analysis, then present a numbered menu of 2–5 complete, viable stacks, with **"Let the AI Agent Decide" always the last option**. Write the option details to TECHNOLOGY_COMPARISON.md first, so they survive an interruption. Wait for the answer unless the user has ordered autonomous execution. A number selects that option; text selects a user-specified stack (respect it if viable). For autonomous selection use the §9.16.5 weighted criteria. Record the choice in DECISIONS.md, PROJECT_STATUS.md ("Stack:" line) and RESUME.md, and never re-ask on resume.
- **Stack profiles** (§9.16.0): menu options come from `toolkit/stacks/README.md` + each `PROFILE.md` (never read skeletons to choose). Run `scripts/check-stack-freshness.sh <profile>` before offering one (ACTION NEEDED → bump by ADR + `scripts/verify-profile.sh`), then `scripts/new-product.sh <profile> <name>` after the selection. A stack without a profile becomes a new profile (`toolkit/stacks/_template/README.md`). Read `toolkit/KNOWN_FACTS.md` before any research.
- **Gate** (§4): before Phase 3, the selection is recorded and `SYSTEM_ARCHITECTURE.md`, `TECH_STACK.md`, `TECHNOLOGY_COMPARISON.md`, `COMPATIBILITY_MATRIX.md` (all 8 columns) and an ADR per major choice exist. Before Phase 4, a compatibility spike on the target runtime has passed.
- Verify versions from official sources, across runtime → framework → libraries → build → DB/driver → broker → base images → CI → hosting (§9.21).
- Never invent version numbers. If a selected technology proves unsuitable: stop the affected work, explain why, and propose an alternative for approval.
- Consistency: code, lock files, Dockerfiles, CI, tests and docs use the approved versions only. A new technology or major version needs ADR → matrix update → approval → tests. Patch/minor updates inside the range are low-risk (record them in ASSUMPTIONS) (§9.21).
- Maintain lock files, dependency/container/secret scans and an SBOM. REVIEW and AUDIT check for stack drift (§9.12, §9.20).
- Record mandated technologies and every deviation from §9, with reason and mitigation, in `TECH_STACK.md`.
