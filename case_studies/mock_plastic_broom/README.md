# Mock plastic broom with a tiny background database

This fixture is the openLCA/Brightway cross-engine form of the LCA REST
engine's `mock_plastic_broom` case study. It contains three reusable fictional
background unit processes plus one foreground assembly process. The bundled
product system is ready to calculate after importing the generated JSON-LD ZIP
into openLCA.

The inventory and method are intentionally synthetic. They test linking,
scaling, inventory aggregation, LCIA, and API plumbing; they must not be used
for environmental claims.

## Supply-chain scaling

```text
Mock plastic broom assembly = 1.0
Mock polypropylene          = 1.0 × 0.52   = 0.52 kg
Mock freight transport      = 1.0 × 0.1055 = 0.1055 tkm
Mock grid electricity       = (0.52 × 2.0) + (0.1055 × 0.08)
                            = 1.04844 kWh
```

## Inventory

```text
Carbon dioxide, fossil
  = (1.04844 × 0.4) + (0.52 × 1.0) + (0.1055 × 0.09)
  = 0.948871 kg

Sulfur dioxide
  = (1.04844 × 0.0003) + (0.52 × 0.0005) + (0.1055 × 0.0001)
  = 0.000585082 kg
```

## LCIA

The included `Mock EF v3.1 subset` method has only two characterization
factors: fossil CO2 = 1.0 kg CO2-Eq/kg and SO2 = 1.31 mol H+-Eq/kg.

```text
Climate change = 0.948871 × 1.0 = 0.948871 kg CO2-Eq
Acidification  = 0.000585082 × 1.31 = 0.00076645742 mol H+-Eq
```

These match the corresponding categories produced by the REST engine's full
EF v3.1 method, within floating-point precision.

## Build and test

```bash
make build CASE=mock_plastic_broom
make release CASE=mock_plastic_broom
make check CASE=mock_plastic_broom
make openlca-foreground CASE=mock_plastic_broom
```

For manual testing, import `mock_plastic_broom.zip` in openLCA, open **Mock
plastic broom product system**, select **Mock EF v3.1 subset**, and calculate.
