# Quality tracker (MASTER_PROMPT §16.9)

| Date | Product / area | Scope | Depth | Score | Δ vs previous | Verdict | Critical | High | Medium | Low | Rework? | Report |
|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---|---|
| 2026-11-21 | WR (workspace rules) | AI Judge integration into the master prompt and rules | Full | 80 | – | APPROVED WITH IMPROVEMENTS | 0 | 1 | 7 | 5 | yes (fixes applied, re-evaluation requested) | workspace-rules/EVAL-2026-11-21-01.md |
| 2026-11-21 | WR (workspace rules) | Re-evaluation after fixes (J-WR-001..013) | Full | 93 | +13 | APPROVED WITH IMPROVEMENTS | 0 | 0 | 0 | 7 | no (Low items tracked) | workspace-rules/EVAL-2026-11-21-02.md |

## Recurring weaknesses
| Weakness | Seen in | Count | Recommended standard / rule change | Status |
|---|---|---:|---|---|
| Build-process traces in client deliverables (user approvals, task IDs, log paths) | disruption-advisor docs, code comments, a new login commit | 3 | Rule added: PRODUCT_RULES §7 (grep before commit/delivery/publish); consider a pre-commit check | Rule in place 2026-11-21 |

## Trend metrics (update at each evaluation)
- Average score: per product/area and overall.
- Open Critical / High findings; rework frequency (evaluations that needed rework / all).
- Test reliability (gate pass rate, flaky tests), deployment failures, production incidents, security findings, documentation completeness.
