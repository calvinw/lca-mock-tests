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
bafu_case_studies/
  plastic_broom/
    build.py         — builds a foreground-only JSON-LD package
    providers.json   — pins openLCA UUIDs and Brightway BAFU activity codes
    olca_ld/         — expanded JSON-LD foreground source
    expected.json    — expected EF v3.1 integration scores
    README.md        — Brightway and openLCA test instructions
scripts/
  ld_dir.py                — shared helper: writes olca_schema entities to
                              an expanded JSON-LD dir, and zips that dir
  make_release.py          — creates mock_lca.zip and a release-ready
                              <case_name>.zip from olca_ld/
  import_to_brightway.py   — imports JSON-LD through the reusable LCA engine
  run_check.py             — checks expected scores through lca_core.LCAEngine
  check_case_study.py      — checks JSON-LD scaling links and inventory,
                              imports into Brightway, then checks LCIA scores
  import_bafu_foreground.py — links JSON-LD exchanges to an installed BAFU DB
  check_bafu_case_study.py  — runs the BAFU-backed integration calculation
```

## Quick start

Dependencies are managed with [`uv`](https://docs.astral.sh/uv/) via
`pyproject.toml` — `uv sync` creates an isolated `.venv/` the first time you
run any command below.

The Brightway path consumes the reusable `lca_core` package from
`life-cycle-assessment-mcp`; it does not invoke the MCP transport. The openLCA
path remains an independent IPC calculation, so both engines consume the same
JSON-LD fixtures through their native import paths.

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

The BAFU-backed integration fixture is intentionally separate from the
hand-computable synthetic suite:

```bash
make bafu-build CASE=plastic_broom
make bafu-release CASE=plastic_broom
make bafu-check CASE=plastic_broom
```

Place the downloaded source packages under the gitignored `source_data/` tree:

```text
source_data/
  bafu/
    BAFU-2026 v1_ecoSpold v1.zip
    BAFU-2026 v1_openLCA.zip
  methods/
    openLCA LCIA Methods 2.8.0 2025-12-15.zip
```

`bafu-check` verifies the EcoSpold checksum and prepares a pristine Brightway
project under `.brightway-test-cache/` on its first run. It then copies that
template to a disposable project, imports the foreground, calculates it
through `lca_core.LCAEngine`, and deletes the disposable project. Run
`make bafu-prepare` to build only the
pristine cache. No existing MCP-server Brightway project is used or modified.

### Automated openLCA IPC checks

Docker must be running. The IPC checks start a disposable openLCA server and
database, import the foreground JSON-LD, create the product system through the
IPC API, calculate it, compare the results with `expected.json`, and remove the
container and temporary database afterward:

```bash
make openlca-foreground                 # all four self-contained mock cases
make openlca-foreground CASE=jacket     # one self-contained case
make openlca-bafu CASE=plastic_broom    # BAFU-backed integration case
make openlca-check                      # both suites
```

The openLCA BAFU check reads these local archives by default:

- `source_data/bafu/BAFU-2026 v1_openLCA.zip`
- `source_data/methods/openLCA LCIA Methods 2.8.0 2025-12-15.zip`

Use `--bafu-archive` and `--methods-archive` with
`scripts/check_openlca.py` to override them. Both checksums are verified. The
BAFU archive is extracted to the gitignored `.openlca-test-cache/`; each run
copies that pristine template, so the source archive and desktop openLCA
databases are never modified.

The first run builds a pinned openLCA 2.7 development server image and reuses
GreenDelta's pinned native UMFPACK/OpenBLAS server layer. The native layer is
required for realistic background-database performance: on the plastic-broom
fixture the 4,551-process calculation takes about five seconds, whereas the
pure-Java fallback takes minutes. Building and running this layer uses
`linux/amd64`, including through Docker's emulation on Apple Silicon.

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

## BAFU integration case studies

| Case study | Tests |
|---|---|
| `plastic_broom` | Imports a foreground-only JSON-LD process after BAFU-2026 v1, links PLA, nylon 6, and freight to three real BAFU providers, and checks EF v3.1 climate change and acidification. |

## Releases

The four MCP-aligned case studies are published as individual
[GitHub Releases](https://github.com/calvinw/lca-mock-tests/releases):
`cotton_fiber-v5`, `jacket-v5`, `polyester_tshirt-v5`, and `wool_yarn-v5`.
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

- `bw2io`'s stock JSON-LD importer only links technosphere/production edges
  *within the same import batch*, and only links biosphere edges against a
  biosphere database built fresh from the current import's own flows —
  neither links against a database written by a *previous* import. The BAFU
  plastic-broom fixture adds a UUID-to-Brightway-code linking layer for its
  technosphere inputs. A generic external biosphere linker is still pending.
- No allocation/co-product test case yet. Brightway-side allocation would
  use the separate `multifunctional` package; openLCA has native allocation
  method support in the schema itself (`AllocationFactor`/`AllocationType`).
- No scenario/Monte Carlo/sensitivity test case yet.

See `PLAN.md` for the prioritized next-steps roadmap.
