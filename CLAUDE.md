# CLAUDE.md

Context for Claude Code working in this repo.

## What this repo is for

A benchmark/regression suite of small, hand-computable LCA supply-chain
graphs, used to cross-validate Brightway 2.5 and openLCA against each other
and against independently hand-calculated expected values, before any of
this logic is trusted against real background databases (ecoinvent/BAFU).

This is infrastructure for a larger, separate project: an agentic LCA tool
for fashion/retail education (built around a `recipe_card.yaml` format and
an LCA MCP server: github.com/calvinw/life-cycle-assessment-mcp). This repo
is deliberately kept independent of that project's recipe-card schema for
now — it's the ground-truth benchmark suite the recipe-card compiler will
eventually be checked against, not the compiler itself.

## Core design decisions (don't relitigate these without a strong reason)

1. **`olca-schema` JSON-LD is the single source of truth format**, not a
   custom YAML/graph schema. It's openLCA's native format, and `bw2io` ships
   a native importer for it (`bw2io.importers.json_ld`). This was chosen
   after determining that `bw_interface_schemas` (a newer, beta,
   Brightway-team-authored graph schema) is *not* consumed by any currently
   working Brightway tooling (verified: zero imports of it anywhere in
   `bw2data`, `bw2calc`, `bw2io`, or `multifunctional`), so building on it
   would mean writing a translation layer to a format nothing downstream
   reads. `olca-schema` is real, tested, and dual-engine-verified.

2. **Every case study author = Python code using the `olca_schema` package's
   typed classes** (`Flow`, `Process`, `Exchange`, `ImpactMethod`,
   `ImpactCategory`, `ImpactFactor`), never hand-typed JSON. `build.py`
   writes those entities to an expanded, checked-in `olca_ld/` directory
   (via the shared `scripts/ld_dir.py` helper) — that directory, not a zip,
   is the source of truth someone can browse in the repo. The importable
   `mock_lca.zip` and descriptively named release copy
   (`<case_study_name>.zip`) are derived, gitignored build artifacts zipped
   from `olca_ld/` on demand (`scripts/make_release.py` / `make release`),
   never hand-edited and never committed.

3. **Every case study ships an `expected.json`** with hand-derived values —
   computed independently, before ever running either engine. Agreement
   between Brightway and openLCA is a secondary, confirmatory check;
   agreement with `expected.json` is the actual ground truth. If a change
   makes an engine disagree with `expected.json`, that's the bug, even if
   the two engines agree with each other.

4. **All product flows use round numbers.** For case studies modeled on a
   real recipe-card teaching example (`cotton_fiber`, `polyester_tshirt`,
   `wool_yarn`), CFs
   instead match that recipe card's real published LCIA method (e.g. TRACI
   v2.1: CH4=25.0, N2O=298.0, NH3=0.1186) so the mock database's numbers
   correspond to the real teaching material, not arbitrary substitutes.
   `expected.json` is still hand-calculated with a calculator in these
   cases (not mental arithmetic) — the goal of catching plumbing bugs by
   comparing against an independently-derived ground truth still holds,
   even where the CF itself isn't a round number.

## Known gotchas

- Every `Process` needs a `location` (even a placeholder `Ref`), or
  `bw2io`'s `json_ld_location_name` strategy raises `KeyError`.
- `ImpactMethod` and `ImpactCategory` need a non-empty `description` field.
- `bw2io`'s `JSONLDExtractor` requires a `locations/` folder to exist in the
  extracted directory (even empty), or `data["locations"]` lookups fail.
- `JSONLDLCIAImporter` needs `.match_biosphere_by_id("<db_name> biosphere")`
  called explicitly before `.write_methods()`, or characterization factors
  come back unlinked (0 CFs matched, LCIA score comes out as 0 or errors).
- **bw2calc demands must target the `product` node, not the `process`
  node.** bw25 enforces the process/product split at calculation time —
  `bc.LCA(demand={process_node: 1}, ...)` raises
  `ValueError: LCA can only be performed on products, not activities`.
  Always look up `type == "product"` when building the demand dict.
- `bw2io`'s JSON-LD technosphere/production linking strategy uses
  `internal=True` — it only links exchanges within the *current* import
  batch. Biosphere linking similarly only searches a biosphere database
  built fresh from the *current* import's own `flows/` folder. Neither
  links against a database written by a previous, separate import. This
  matters a lot once a case study is split into separate
  background/foreground zips (see Phase 2 in the roadmap below) — a custom
  linking strategy pointed at the already-written database will be needed
  on both the technosphere and biosphere side.

## Conventions

- Case study folder name = snake_case and matches the reference product's
  rough identity (`cotton_fiber`, `polyester_tshirt`, etc.).
- Real-background integration fixtures live under `bafu_case_studies/`, not
  under the hand-computable `case_studies/` suite. Keep BAFU immutable: these
  packages contain foreground entities and external references only.
- Flow/process names use concise domain names without a `Mock` prefix; the
  repository context identifies these as synthetic test datasets.
- Commit `build.py`, `expected.json`, and the `olca_ld/` directory. Never
  commit `mock_lca.zip`, `<case_study_name>.zip`, `ids.txt`, `_extracted/`,
  or `.bw_project/` — they're all build/import artifacts, gitignored, and
  should be regenerated from the checked-in source (see below).
- `expected.json` also carries `reference_product`, `method_name`, and
  `impact_category` fields (in addition to the hand-derived
  `scaling_vector`/`inventory`/`score`) — this metadata is what
  `scripts/check_case_study.py` uses to run the check generically without
  per-case-study hardcoding.
- Dependencies are managed with `uv` (`pyproject.toml` + `uv.lock`), not
  bare `pip install`. Prefix Python invocations with `uv run`.
- If a case study is published as a GitHub Release, upload the generated
  `<case_study_name>.zip` asset (e.g. `cotton_fiber.zip`), not the generic
  `mock_lca.zip` check artifact. GitHub always attaches automatic "Source code
  (zip/tar.gz)" links to any tag-based release; that can't be suppressed
  per-release via `gh`/the API, so don't try.

## How to verify a change didn't break anything

```bash
make all         # build + release (zip) + check every case study
# or, for a single case study:
make build   CASE=cotton_fiber
make release CASE=cotton_fiber
make check   CASE=cotton_fiber
make clean   CASE=cotton_fiber   # removes imported projects and generated ZIPs
```
`make check`/`all-check` runs `scripts/check_case_study.py`, which imports
the zip into a fresh Brightway project and diffs the computed score against
`expected.json`, using the `reference_product`/`method_name`/
`impact_category` recorded there. This is a manual step run via the
Makefile, not yet wired into GitHub Actions CI — see roadmap Phase 1 in
`PLAN.md`.
