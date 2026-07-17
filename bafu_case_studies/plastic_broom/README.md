# Plastic Broom with BAFU Background

This is a foreground-after-background integration case. Unlike the synthetic
cases under `case_studies/`, the JSON-LD package contains only the plastic
broom assembly process and its output. Its three technosphere inputs reference
real providers in **BAFU-2026 v1**, prepared automatically from the downloaded
source archives under `source_data/bafu/`.

## What it tests

- openLCA resolves external product-flow and default-provider UUIDs after the
  BAFU database is installed.
- Brightway prepares and caches `bafu` from the downloaded EcoSpold archive,
  then imports the foreground JSON-LD into a disposable project and links it.
- One plastic broom calculates to the production MCP baseline under EF v3.1.
- No BAFU process is copied into or modified by the foreground package.

The provider identities and both BAFU archive checksums are pinned in
`providers.json`.

## Build and check with Brightway

From the repository root:

```bash
make bafu-build CASE=plastic_broom
make bafu-release CASE=plastic_broom
make bafu-prepare
make bafu-check CASE=plastic_broom
```

The first preparation imports the EcoSpold source, biosphere3, and bundled
Brightway LCIA methods into `.brightway-test-cache/`. The check copies that
pristine project, imports the foreground as `bafu plastic broom foreground`,
asserts that all three inputs point to the expected BAFU activity codes, checks
the scores, and deletes the project copy.

## Test with openLCA

1. Import the exact `BAFU-2026 v1_openLCA.zip` database first.
2. Build `plastic_broom_bafu.zip` with `make bafu-release CASE=plastic_broom`.
3. Import that ZIP with **File → Import → openLCA JSON-LD**.
4. Open **Plastic broom — BAFU-2026 v1 (foreground seed)** under Product
   systems and verify that its three direct process links resolve.
5. Open **Plastic broom assembly** under Processes and create a new product
   system with automatic linking enabled and default providers preferred. This
   step expands the already-installed BAFU upstream graph; the foreground seed
   intentionally contains only the three direct links.
6. Calculate the automatically linked system with EF v3.1 and compare climate
   change and acidification with `expected.json`.

If openLCA reports missing references, verify the BAFU archive checksum against
`providers.json`; another BAFU export may use different UUIDs.
