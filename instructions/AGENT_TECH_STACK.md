# AI Agent Technology Stack (records per MASTER_PROMPT §9.24.3 and §9.24.8)

This is the agent's own stack: what runs the engineering organisation, kept separate from any product stack (§9.24.1).
It is a workspace record and is never delivered with a product (`instructions/`, `toolkit/` and `scripts/` stay out of product folders).
Verified 2026-11-20 on the developer workstation. Update this file when the runtime changes. Do not copy rules from the documents linked below; link to them.

## Decision (D-015)
- **No custom agent backend is built.** The agent is Claude Code, driven by the master prompt plus file-based state.
- Building our own runtime (§9.24.3.4: Python, TypeScript or Java with LangGraph or similar) would add code to maintain without meeting any requirement.
- This is not asked of the user, because it doesn't change their environment, costs or security (§9.24.4).
- **Re-evaluate** if the agent must run unattended as a service, run on a schedule, or serve several users. §9.24.3.4–§9.24.3.9 then apply in full, including §13 and §14 for its runtime.

| Area (§9.24.8) | Current implementation | Authoritative source |
|---|---|---|
| Runtime architecture | Claude Code CLI 2.1.329 on the developer workstation (Linux). One coordinating agent that plays the organisation's roles; subagents only for parallel or isolated work | `CLAUDE.md`, `instructions/MASTER_PROMPT.md` §1, §4 |
| Model provider | Anthropic models through Claude Code. The model is chosen in the Claude Code settings (`/model`), not hard-coded in the workspace. Claude Code handles retries and rate limits | Claude Code configuration |
| Orchestration | No framework. Claude Code's own loop, with the phase and gate workflow from the master prompt | MASTER_PROMPT §4, §9.16 |
| Tools and MCP | Built-in Claude Code tools: shell, file read/edit, search, subagents. MCP connectors may be attached to the account; products don't depend on any of them. Helper scripts in `scripts/`. Stack profiles in `toolkit/` | `scripts/`, `toolkit/README.md` |
| Memory and execution state | Markdown files are authoritative (`execution/RESUME.md`, `CURRENT_TASK.md`, `PROJECT_STATUS.md`, `DECISIONS.md`, `DEPLOYMENT_STATUS.md`, logs). No database or vector store | `instructions/CHECKPOINT_PROTOCOL.md` |
| Automatic logging and recovery | Python 3.12 hook `.claude/hooks/checkpoint_hook.py`, wired in `.claude/settings.json`. It logs every tool call with secrets redacted, writes session markers, and injects `RESUME.md` at session start. Fail-safe: always exits 0 | CHECKPOINT_PROTOCOL §0, §8 |
| Security boundaries | Claude Code permission modes (the user approves or declines tool calls). Secrets are never committed: `.gitignore` covers `input/` secrets and the cloud key. Hook redaction. Disruptive server and production actions need explicit user authorization. Retrieved content is treated as data, not instructions | `instructions/SECURITY_RULES.md`, `instructions/DEPLOYMENT_RULES.md` |
| Sandbox and isolation | Work happens in the workspace git repo. Each product builds and tests independently in its own folder (Docker, Testcontainers). Temporary files go to the session scratchpad | `instructions/PRODUCT_RULES.md` |
| Evaluation and observability | `tool-activity.log` (ok/FAIL per call), `errors.log`, `sessions.log` (TurnFailed = API or connection error). Outcomes are checked by real builds, tests and saved output (`execution/logs/output/`), never by the model's own claim. Token and cost tracking comes from Claude Code (`/cost`, `/usage`). There is no separate evaluation dataset yet (gap, low priority while there is a single user) | CHECKPOINT_PROTOCOL §0, §5 |
| Deployment and recovery | Not deployed as a service. Recovery is the resume protocol: a session can stop at any moment and the next one continues from the files | CLAUDE.md, CHECKPOINT_PROTOCOL §8 |

## Known gaps (accepted, revisit at re-evaluation)
- No automated agent evaluation suite (§9.24.3.7). Quality is checked by product gates and tests.
- No central metrics or tracing (OpenTelemetry/Langfuse). The log files are enough for one local operator.
