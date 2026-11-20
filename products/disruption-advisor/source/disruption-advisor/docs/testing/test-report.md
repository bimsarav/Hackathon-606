# Test Report (MVP)

All results come from real runs on 2026-11-20. Commands are in the README. Logs are in `logs/` and are not committed.

## Local quality gate: `scripts/check.sh`
| Step | Result |
|---|---|
| Backend lint (Ruff, incl. security rules `S`) | PASS. `S608` is excepted for `app/engine/store.py` and `app/ingest/*`, where SQL interpolates only constant names and configured paths; user values are bound parameters (see `pyproject.toml`) |
| Backend format, mypy strict | PASS |
| Backend tests (pytest + Testcontainers PostgreSQL 18, Alembic) | **22 passed**; coverage 78% (the ingest is exercised by the real-data run below, not by unit tests) |
| Frontend type check (`tsc` strict), unit tests (Vitest), production build | PASS: **5 tests** |

The engine tests use a hand-made network (`backend/tests/ops_fixture.py`) and cover:
- delay propagation through turn times, and slack absorbing the delay;
- a same-type swap that removes the knock-on delay, and rejection of an infeasible swap;
- the option ranking;
- misconnects against the hub MCT table;
- cancellation: tier order, families kept together, non-revenue passengers last, an OPTIMAL seat assignment, and weights that never cross tiers;
- the EU261 bands;
- loading the store.

The API tests cover:
- authentication: wrong password, missing or forged token;
- both scenarios end to end;
- what-if weights, decisions (audit), message drafts;
- validation errors (RFC 9457) and 404s;
- that migrations match the models.

## Real-data run (local Docker Compose, then the server)
- **Ingest** (in the container), with the result also recorded in `ops/ingest_report.json`:
  - 27,879,509 booking rows converted to Parquet; 2 malformed lines rejected; 1 truncated inventory line skipped.
  - Built: 4,646 flights, 299,419 passenger segments in the window, 174,723 customer profiles.
- **Scenario A, G9519 DAC→SHJ, +150 min:**

  | Option | Delay | Legs | Missed connections | Cost |
  |---|---|---|---|---|
  | Absorb the delay | 480 min | 5 | 90 | AED 222,600 |
  | Swap in A6-ARI (recommended) | 150 min | 1 | 33 | AED 70,875 |

  Of the 33 passengers who still miss a connection, 31 are rebooked within 24 h. The explanation was written by `claude-opus-5-5` from the engine's figures; the request took about 4 s through nginx.
- **Scenario B, cancellation G9562 SHJ→LYP:** 147 passengers and 60 free seats on the alternatives. CP-SAT solved it OPTIMAL in under 1 s: 60 passengers protected by tier and score, 87 offered next day with hotel.

## End-to-end: `scripts/e2e.sh` (Playwright 1.65.1, Chromium)
| Target | Result |
|---|---|
| Local stack `http://localhost:8888` | **3 passed**: wrong password rejected, and the API needs a token; scenario A assessed, options compared and the recommendation approved; scenario B tier order, what-if re-run, message draft and plan approved |
| Server `http://<server>:8888` | **3 passed** before and after the reboot test; smoke test 11/11 (see `docs/deployment/DEPLOYMENT_GUIDE.md`) |

## Security scans (Trivy 0.76.2, HIGH/CRITICAL)
| Target | Result |
|---|---|
| Repository: `uv.lock`, `package-lock.json`, Dockerfiles (dependencies, secrets, misconfiguration) | 0 findings |
| Image `disruption-advisor-web` | 0 findings |
| Image `disruption-advisor-api` | 0 vulnerabilities. The secret-rule matches (`gcp-service-account`) are **false positives** in the Anthropic SDK's own docstrings (the text `"type": "service_account"` in `anthropic/resources/beta/agents/*.py`); no credential is present |
