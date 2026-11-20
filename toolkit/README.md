# toolkit/: reusable, pre-verified building blocks (AI working material)

Pays the cost of technology selection, version research and compatibility proof **once**, then reuses it for every product (MASTER_PROMPT §9.16, PRODUCT_RULES §1). Like `instructions/` and `execution/`, it is never delivered: products receive a **copy**, through `scripts/new-product.sh`.

| Path | What it is |
|---|---|
| [stacks/README.md](stacks/README.md) | Catalogue of stack profiles: which to offer in the selection menu, and status |
| `stacks/<profile>/` | One verified stack: `PROFILE.md` (menu card), `VERIFIED.md` (last proof), `freshness.conf`, `docs/` (architecture templates + ADRs), `skeleton/` (working repo) |
| [stacks/_template/README.md](stacks/_template/README.md) | Contract for adding a new profile |
| [KNOWN_FACTS.md](KNOWN_FACTS.md) | Verified environment facts and pitfalls. Read before any research or debugging |

Scripts (workspace `scripts/`):
| Command | Use |
|---|---|
| `scripts/check-stack-freshness.sh <profile>` | Before offering or using a profile: verification age, runtime support (endoflife.date), outdated dependencies. Exit 0 = FRESH |
| `scripts/new-product.sh <profile> <product-name>` | Creates `products/<name>/source/<name>/` from the profile (renames the sample identifiers) |
| `scripts/verify-profile.sh <profile>` | Re-proves a profile (generate copy → quality gate → Compose smoke → Trivy) and rewrites its `VERIFIED.md` |

Token rule: never read a profile's skeleton to choose a stack. `stacks/README.md` and `PROFILE.md` are enough. Read skeleton files only when changing them.
