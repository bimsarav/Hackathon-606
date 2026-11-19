# Documentation Rules
- Product documentation lives inside the product repo under `docs/` (business, architecture + ADRs, api, data, security, testing, deployment, runbooks, delivery report, traceability matrix).
- The repo `README.md` is the entry point: what it is, prerequisites, quick start, build, test, run, deploy, push to git, configuration reference, links to `docs/`.
- `products/<product-name>/CONFLUENCE_PAGE.md` follows PRODUCT_RULES §6 (Confluence-safe Markdown, self-contained, no Mermaid, HTML or relative links).
- Generated artefacts (OpenAPI specs) are produced by the build and checked in, never hand-edited.
- Requirement IDs (FR-x, NFR-x, BR-x) are used consistently across docs, code comments and tests.
