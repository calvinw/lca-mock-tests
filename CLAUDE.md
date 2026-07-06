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
   `ImpactCategory`, `ImpactFactor`), never hand-typed JSON. Serialize with
   `olca_schema.zipio.ZipWriter`.

3. **Every case study ships an `expected.json`** with hand-derived values —
   computed independently, before ever running either engine. Agreement
   between Brightway and openLCA is a secondary, confirmatory check;
   agreement with `expected.json` is the actual ground truth. If a change
   makes an engine disagree with `expected.json`, that's the bug, even if
   the two engines agree with each other.

4. **All product flows use round numbers, all CFs are trivial integers**
   (e.g. CF=1, CF=10) — so every case study's expected values can be
   verified by hand-arithmetic, not just trusted from a solver.

## Known gotchas (hit while building `mock_widget`, will recur in new cases)

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

- Case study folder name = snake_case, matches the reference product's
  rough identity (`mock_widget`, `mock_coproduct`, etc.)
- Flow/process names always prefixed `Mock ` so they're never mistaken for
  real ecoinvent/BAFU data during debugging.
- Don't commit generated `.zip` files or `_extracted/`/`.bw_project/`
  directories — they're build artifacts, regenerate them from `build.py`.

## How to verify a change didn't break anything

```bash
for cs in case_studies/*/; do
    python "$cs/build.py"
    python scripts/import_to_brightway.py "$cs/mock_lca.zip" \
        "$(basename $cs) background" "$(basename $cs)_test"
    python scripts/run_check.py "$(basename $cs)_test" \
        "$(basename $cs) background" "Mock LCIA Method" "Mock GWP" \
        "Mock Widget" "$cs/expected.json"
done
```
(This loop is a starting point, not yet a real CI script — see roadmap
Phase 1.)
