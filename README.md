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
    build.py         — builds the graph + LCIA method, writes olca_ld/
    olca_ld/         — expanded, checked-in JSON-LD (flows/, processes/,
                       lcia_categories/, lcia_methods/, unit_groups/) --
                       this is the browsable source of truth for the
                       database structure
    expected.json    — hand-calculated ground truth (scaling vector,
                       inventory, impact score, plus the reference
                       product/method/category names used to check it)
    mock_lca.zip     — regenerated on demand from olca_ld/, gitignored
scripts/
  ld_dir.py                — shared helper: writes olca_schema entities to
                              an expanded JSON-LD dir, and zips that dir
  make_release.py          — zips a case study's olca_ld/ into mock_lca.zip
  import_to_brightway.py   — generic JSON-LD zip → Brightway project importer
  run_check.py             — runs bw2calc against an imported case study and
                              checks the result against expected.json
  check_case_study.py      — import_to_brightway.py + run_check.py in one
                              step, reading metadata from expected.json
```

## Quick start

Dependencies are managed with [`uv`](https://docs.astral.sh/uv/) via
`pyproject.toml` — `uv sync` creates an isolated `.venv/` the first time you
run any command below.

```bash
# Build, release (zip), and check every case study
make all

# Or work on a single case study:
make build   CASE=mock_widget   # build.py -> writes case_studies/mock_widget/olca_ld/
make release CASE=mock_widget   # zips olca_ld/ -> case_studies/mock_widget/mock_lca.zip
make check   CASE=mock_widget   # imports the zip into Brightway, checks vs expected.json
make clean   CASE=mock_widget   # removes .bw_project/, _extracted/, mock_lca.zip
```

Equivalent raw commands (what the Makefile targets run under the hood):

```bash
uv run python case_studies/mock_widget/build.py
uv run python scripts/make_release.py case_studies/mock_widget
uv run python scripts/check_case_study.py case_studies/mock_widget
```

To test the same zip in **openLCA**: File → Import → openLCA JSON-LD Zip
File → select `case_studies/mock_widget/mock_lca.zip` → create a product
system from the reference process → Calculate → compare the result to
`expected.json`.

## Current case studies

| Case study | Tests |
|---|---|
| `mock_widget` | Basic linear chain (2 levels deep), no allocation, no loops. Sanity check for matrix solve + characterization. |
| `mock_cotton_fiber` | 2-process chain, two impact categories at once (GWP + eutrophication) sharing a common emission (N2O). |
| `mock_polyester_tshirt` | 3-process chain (2 levels deep), compound scaling across two supply-chain hops. |
| `mock_wool_yarn` | 2-process chain, tests a >1.0 scaling factor (process loss) and CH4's outsized GWP contribution. |

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
