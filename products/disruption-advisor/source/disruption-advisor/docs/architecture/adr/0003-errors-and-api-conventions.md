# ADR-0003: API conventions: versioning, problem details, validation, paging

- **Status:** Accepted (2026-11-20)
- **Context:** The API needs versioning, consistent error responses, input validation and paging conventions.
- **Decision:** Every route lives under `/api/v1`. All errors, including validation and unhandled ones, use RFC 9457 `application/problem+json` (`type`, `title`, `status`, `detail`, optional `errors[]` with `loc` and `msg`). Request models use `extra="forbid"`, whitespace stripping and length limits. Lists take `limit` (1–100, default 50) and `offset`, and return `{items, limit, offset}`. Every response carries `X-Request-ID`.
- **Consequences:** One error-handling path in the client (`ApiError` in `frontend/src/api.ts`); breaking changes need `/api/v2`.
