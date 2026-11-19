# Business Rules
Business rules are specific to each product. They are defined during Phase 1 from the requirement in `input/`, then kept in the product repo at `products/<product-name>/source/<product-name>/docs/business/business-rules.md`.
This file only holds rules that apply to every product:
- Never invent business rules. Ask the product owner. If a default is needed to keep going, make it configurable, mark it "pending approval" and record it in `execution/ASSUMPTIONS.md`.
- Every rule has a stable ID (BR-x) that is traced to code and tests.
