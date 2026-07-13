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

This repo is a suite of small, deliberately synthetic supply-chain graphs where
every intermediate number (scaling vector, inventory, impact score) can be
computed by hand. The three MCP-aligned studies use the corresponding TRACI v2.1 factors
so their results can be compared directly with the LCA MCP server. The suite
exists to catch plumbing bugs *before* they hide inside real data and to serve
as a regression suite for a future recipe-card-to-engine compiler.

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
  <case_name>/
    build.py         — builds the graph + LCIA method, writes olca_ld/
    olca_ld/         — expanded, checked-in JSON-LD (flows/, processes/,
                       lcia_categories/, lcia_methods/, unit_groups/) --
                       this is the browsable source of truth for the
                       database structure
    expected.json    — hand-calculated ground truth (scaling vector,
                       inventory, impact score, plus the reference
                       product/method/category names used to check it)
    README.md        — derivation of the expected scaling, inventory,
                       and LCIA scores by hand
    mock_lca.zip     — regenerated on demand from olca_ld/, gitignored
    <case_name>.zip  — identical, release-ready asset with a descriptive name
scripts/
  ld_dir.py                — shared helper: writes olca_schema entities to
                              an expanded JSON-LD dir, and zips that dir
  make_release.py          — creates mock_lca.zip and a release-ready
                              <case_name>.zip from olca_ld/
  import_to_brightway.py   — generic JSON-LD zip → Brightway project importer
  run_check.py             — checks all expected LCIA scores with bw2calc
  check_case_study.py      — checks JSON-LD scaling links and inventory,
                              imports into Brightway, then checks LCIA scores
```

## Quick start

Dependencies are managed with [`uv`](https://docs.astral.sh/uv/) via
`pyproject.toml` — `uv sync` creates an isolated `.venv/` the first time you
run any command below.

```bash
# Build, release (zip), and check every case study
make all

# Or work on a single case study:
make build   CASE=cotton_fiber   # build.py -> writes case_studies/cotton_fiber/olca_ld/
make release CASE=cotton_fiber   # creates mock_lca.zip and cotton_fiber.zip
make check   CASE=cotton_fiber   # imports the zip into Brightway, checks vs expected.json
make clean   CASE=cotton_fiber   # removes imported projects and generated ZIPs
```

Equivalent raw commands (what the Makefile targets run under the hood):

```bash
uv run python case_studies/cotton_fiber/build.py
uv run python scripts/make_release.py case_studies/cotton_fiber
uv run python scripts/check_case_study.py case_studies/cotton_fiber
```

To test the same zip in **openLCA**: File → Import → openLCA JSON-LD Zip
File → select a case study's descriptively named zip → open the included product
system under **Product systems** → Calculate → compare the result to
`expected.json`. Water in the cotton and wool examples is an elementary
resource input (8,000 L and 30 L respectively), so it appears in the inventory
even though the included LCIA categories do not characterize it.

## Current case studies

| Case study | Tests |
|---|---|
| `cotton_fiber` | 2-process chain with GWP, eutrophication, acidification, and particulate matter formation: N2O drives GWP, NH3 drives the other three categories, and water extraction tests a volume resource input. |
| `jacket` | 5-process, 3-tier chain with a parallel zipper branch. Tests compound scaling over three upstream levels, multiple providers at jacket assembly, and methane/NOx contributions across five TRACI categories. |
| `polyester_tshirt` | 3-process chain (2 levels deep), compound scaling across two supply-chain hops, plus methane contributions to GWP and photochemical oxidant formation. |
| `wool_yarn` | 2-process chain, tests a >1.0 scaling factor (process loss), methane contributions to GWP and photochemical oxidant formation, and water extraction. |

## Releases

The three MCP-aligned case studies are published as individual
[GitHub Releases](https://github.com/calvinw/lca-mock-tests/releases):
`cotton_fiber-v5`, `polyester_tshirt-v5`, and `wool_yarn-v5`.
Each release contains a versioned, importable ZIP with a pre-linked openLCA
Product System. To cut a new
version after editing a case study:

```bash
make build CASE=cotton_fiber
make release CASE=cotton_fiber
make check CASE=cotton_fiber                 # verify before publishing
git tag -a cotton_fiber-v6 -m "Release cotton_fiber-v6"
git push origin cotton_fiber-v6
cp case_studies/cotton_fiber/cotton_fiber.zip /tmp/cotton_fiber-v6.zip
gh release create cotton_fiber-v6 /tmp/cotton_fiber-v6.zip \
  --title "Cotton Fiber v6"
```

GitHub automatically attaches "Source code (zip/tar.gz)" links to any
tag-based release — that's generated from the tag itself and can't be
suppressed per-release.

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
