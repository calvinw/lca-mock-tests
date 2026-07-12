# Polyester T-shirt hand calculations

This case represents the production of one polyester T-shirt. These calculations
are the independent ground truth recorded in `expected.json` and checked against
Brightway.

## Process scaling

T-shirt assembly runs once and consumes 0.2 kg of polyester fiber. Producing
that fiber consumes 1.5 kg of crude oil per kg of fiber.

```text
s_tshirt = 1.0
s_fiber  = 1.0 × 0.2       = 0.2
s_oil    = 1.0 × 0.2 × 1.5 = 0.3
```

## Inventory totals

```text
CO2 = (0.3 × 0.2) + (0.2 × 5.5) + (1.0 × 1.0) = 2.16 kg
CH4 = 0.3 × 0.05                                  = 0.015 kg
```

## LCIA results

The characterization factors match the TRACI v2.1 factors used by the
corresponding LCA MCP teaching case.

```text
GWP = (2.16 × 1) + (0.015 × 25)       = 2.535 kg CO2-eq
MIR = 0.015 × 0.014379488             = 0.00021569232 kg O3-eq
```
