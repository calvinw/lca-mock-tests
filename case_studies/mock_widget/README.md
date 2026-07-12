# Mock widget

`mock_widget` is the suite's basic plumbing example. It uses four processes,
simple characterization factors, and hand-computable values to test product
linking, matrix scaling, inventory aggregation, and LCIA calculation.

## Expected result

- Scaling vector: electricity 6.0, steel 3.0, transport 5.0, widget 1.0
- Inventory: 6.5 kg Mock CO2 and 0.02 kg Mock CH4
- Mock GWP: 6.7 kg Mock-CO2-eq

The expected values are recorded in `expected.json`.

## Build and verify

Run these commands from the repository root:

```bash
make build CASE=mock_widget
make release CASE=mock_widget
make check CASE=mock_widget
```

`build` regenerates the expanded `olca_ld/` source, `release` creates both
`mock_lca.zip` and `mock_widget.zip`, and `check` validates the source graph
before importing it into Brightway and comparing the calculated result with
`expected.json`.

To verify it in openLCA, import `mock_widget.zip` as an openLCA JSON-LD ZIP,
create a product system for `Mock Widget production`, calculate with
`Mock LCIA Method` / `Mock GWP`, and compare the result above.
