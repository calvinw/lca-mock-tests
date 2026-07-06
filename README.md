# lca-mock-tests

Small, hand-computable LCA test graphs used to cross-validate two calculation
engines — **Brightway 2.5** (`bw2data`/`bw2calc`/`bw2io`) and **openLCA** —
against each other and against independently hand-calculated expected values.

## Why this exists

Real LCA background databases (ecoinvent, BAFU) are too large and too
methodologically entangled to hand-verify. If two engines disagree on a real
case study, you can't easily tell whether the cause is a genuine LCA
methodology difference (allocation choice, characterization factors) or a
plumbing bug (a silently unlinked exchange, a unit conversion error, a flow
identity mismatch).

This repo is a small, deliberately synthetic supply chain graph — round
numbers, trivial characterization factors — where every intermediate number
(scaling vector, inventory, impact score) can be computed by hand. It exists
to catch plumbing bugs *before* they hide inside real data, and to serve as a
regression suite for a future recipe-card-to-engine compiler.

## Format

Each case study is authored once, in Python, using GreenDelta's
[`olca-schema`](https://github.com/GreenDelta/olca-schema) package, and
exported as an `olca-schema` JSON-LD zip — openLCA's own native format.
`bw2io` ships a native importer for this exact format
(`bw2io.importers.json_ld.JSONLDImporter` /
`bw2io.importers.json_ld_lcia.JSONLDLCIAImporter`), so **one file imports
cleanly into both engines** without a separate translation layer.

## Repo structure

```
case_studies/
  mock_widget/
    build.py        — builds the graph + LCIA method, writes the JSON-LD zip
    expected.json    — hand-calculated ground truth (scaling vector,
                       inventory, impact score)
    README.md        — gotchas hit while building this specific case,
                       and the case's supply chain description
scripts/
  import_to_brightway.py  — generic JSON-LD → Brightway project importer
  run_check.py             — runs bw2calc against an imported case study and
                              checks the result against expected.json
```

## Quick start

```bash
pip install olca-schema bw2data bw2calc bw2io --break-system-packages

# Build the JSON-LD zip for a case study
python case_studies/mock_widget/build.py
# -> writes case_studies/mock_widget/mock_lca.zip

# Import into a Brightway project (writes Brightway's data dir to
# case_studies/mock_widget/.bw_project by default)
python scripts/import_to_brightway.py \
    case_studies/mock_widget/mock_lca.zip "mock background" mock_lca_test

# Run the LCA and check it against the hand-calculated expected value
python scripts/run_check.py \
    case_studies/mock_widget/.bw_project mock_lca_test "mock background" \
    "Mock LCIA Method" "Mock GWP" "Mock Widget" \
    case_studies/mock_widget/expected.json
```

To test the same zip in **openLCA**: File → Import → openLCA JSON-LD Zip
File → select the generated zip → create a product system from the
reference process → Calculate → compare the result to `expected.json`.

## Current case studies

| Case study | Tests |
|---|---|
| `mock_widget` | Basic linear chain (2 levels deep), no allocation, no loops. Sanity check for matrix solve + characterization. |

## Known gaps (see `PLAN.md` for the full roadmap)

- `bw2io`'s JSON-LD importer only links technosphere/production edges
  *within the same import batch*, and only links biosphere edges against a
  biosphere database built fresh from the current import's own flows —
  neither links against a database written by a *previous* import. A
  foreground-imported-after-background scenario (the real BAFU workflow)
  needs custom linking strategies added on top of the default import.
- No allocation/co-product test case yet. Brightway-side allocation would
  use the separate `multifunctional` package; openLCA has native allocation
  method support in the schema itself (`AllocationFactor`/`AllocationType`).
- No scenario/Monte Carlo/sensitivity test case yet.

See `PLAN.md` for the prioritized next-steps roadmap.
