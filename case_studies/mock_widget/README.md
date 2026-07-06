# Mock LCA cross-engine test case

Three scripts, run in order, plus the resulting JSON-LD zip.

1. `build.py` — builds the mock background+foreground graph (4 processes,
   6 flows, 4 unit groups) and the Mock LCIA Method using the `olca_schema`
   package, and writes `mock_lca.zip` (olca-schema / JSON-LD format).
   Requires: `pip install olca-schema --break-system-packages`

2. `run_bw.py` — extracts `mock_lca.zip` and imports it into a real
   Brightway project using bw2io's native `JSONLDImporter` and
   `JSONLDLCIAImporter`. Requires an extracted copy of the zip at
   `./extracted/` (with an added empty `locations/` folder — see notes below)
   and: `pip install bw2io bw2data bw2calc --break-system-packages`

3. `run_lca.py` — opens the resulting Brightway project, demands 1 unit of
   the **Mock Widget product** (not the process node — bw25 requires the
   product), runs bw2calc, and prints the scaling vector, inventory, and
   characterized score.

## Expected result (hand-calculated, confirmed in both Brightway and openLCA)

Scaling vector: Electricity=6.0, Steel=3.0, Transport=5.0, Widget=1.0
Inventory: Mock CO2 = 6.5 kg, Mock CH4 = 0.02 kg
Mock GWP score: 6.7 kg Mock-CO2-eq

## Notes / gotchas hit while building this

- Every process needs a `location` (even a dummy one) or bw2io's
  `json_ld_location_name` strategy raises a KeyError.
- `ImpactMethod`/`ImpactCategory` need a non-empty `description`.
- bw2io's `JSONLDExtractor` needs a `locations/` folder to exist (even
  empty) or `data["locations"]` lookups fail.
- `JSONLDLCIAImporter` needs `.match_biosphere_by_id("mock background biosphere")`
  called explicitly before `.write_methods()`, or the characterization
  factors come back unlinked.
- `bw2io`'s JSON-LD importer only links technosphere/production edges
  *within the same import batch* (`internal=True`) and only links
  biosphere edges against a biosphere database built fresh from the
  *current* import's own `flows/` folder — neither links against a
  previously-written database. Fine for this single-file test; would
  need custom linking strategies for a split foreground/background
  import.
