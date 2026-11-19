# Next Action
- **Action:** When the user says the requirement data is in `input/`: confirm whether the existing ESMP pack in `input/inbox/` (committed as "Can drop") is part of it, sort the inbox into `input/` subfolders, choose and record the product name, create `products/<product-name>/source/<product-name>/`, and run Phase 1 per `instructions/PRODUCT_RULES.md`.
- **Files:** `input/**`, `products/<product-name>/**`, `execution/*`
- **Prerequisites:** The user has added the requirement data; read `instructions/PRODUCT_RULES.md` first.
- **Expected outcome:** Product folder scaffolded; requirements analysis and grouped clarification questions.
- **Validation:** Every requirement traces back to an input document or a user answer.
- **Risks:** Treating dropped material as a requirement; inventing requirements.
