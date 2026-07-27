# Simple mock plastic broom with one grid-electricity link

This fixture is a simplified variant of `mock_plastic_broom`. It contains the
same four fictional unit processes, but grid electricity is consumed only by
polypropylene production. Freight has direct emissions and no electricity
input. The bundled product system is ready to calculate after importing the
generated JSON-LD ZIP into openLCA.

The inventory and method are intentionally synthetic. They test linking,
scaling, inventory aggregation, LCIA, and API plumbing; they must not be used
for environmental claims.

## Supply-chain scaling

```text
Simple mock plastic broom assembly = 1.0
Mock polypropylene                = 1.0 × 0.52 = 0.52 kg
Mock freight transport            = 1.0 × 0.1055 = 0.1055 tkm
Mock grid electricity             = 0.52 × 2.0 = 1.04 kWh
```

The grid supplies only `Mock polypropylene granulate, at plant`; there is no
grid-electricity exchange on freight or broom assembly.

## Inventory

```text
Carbon dioxide, fossil
  = (1.04 × 0.4) + (0.52 × 1.0) + (0.1055 × 0.09)
  = 0.945495 kg

Sulfur dioxide
  = (1.04 × 0.0003) + (0.52 × 0.0005) + (0.1055 × 0.0001)
  = 0.00058255 kg
```

## LCIA

The included `Mock EF v3.1 subset` method has only two characterization
factors: fossil CO2 = 1.0 kg CO2-Eq/kg and SO2 = 1.31 mol H+-Eq/kg.

```text
Climate change = 0.945495 × 1.0 = 0.945495 kg CO2-Eq
Acidification  = 0.00058255 × 1.31 = 0.0007631405 mol H+-Eq
```

## Build and test

```bash
make build CASE=mock_plastic_broom_simple
make release CASE=mock_plastic_broom_simple
make check CASE=mock_plastic_broom_simple
make openlca-foreground CASE=mock_plastic_broom_simple
```

For manual testing, import `mock_plastic_broom_simple.zip` in openLCA, open
**Simple mock plastic broom product system**, select **Mock EF v3.1 subset**,
and calculate.
