# python-fastapi: verification record

Verified: 2026-11-19 · Status: **PASS** · Host: Docker 20.10.24, Compose 2.21.0

Produced by `scripts/verify-profile.sh python-fastapi`. Do not edit by hand; re-run the script instead.
A profile whose last PASS is older than 30 days needs `scripts/check-stack-freshness.sh python-fastapi` before use (MASTER_PROMPT §9.16.0).

| Step | Result |
|---|---|
| generate product copy (scripts/new-product.sh) | PASS |
| quality gate (scripts/check.sh): 9 passed in 2.39s; Tests 5 passed (5) | PASS |
| deployment smoke test (scripts/smoke.sh): 12 checks | PASS |
| Trivy fs: dependencies, secrets, Dockerfile/compose misconfiguration (HIGH/CRITICAL) | PASS |
| Trivy image verify-python-fastapi-api:latest: 0 fixable HIGH/CRITICAL | PASS |
| Trivy image verify-python-fastapi-web:latest: 0 fixable HIGH/CRITICAL | PASS |
