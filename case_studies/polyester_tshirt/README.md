# Polyester T-shirt hand calculations

This case represents the production of one polyester T-shirt. These calculations
are the independent ground truth recorded in `expected.json` and checked against
Brightway.

## Supply-chain structure

![Supply-chain structure](structure.svg)

This image shows the product graph with the flow types but without yet the
actual flow amounts. Blue boxes are unit processes, gray arrows carry products
or intermediate materials between them, and the purple box is the functional
unit. Green arrows are extractions from nature; red arrows are emissions to the
environment.

## Unit-process Diagrams (unscaled)

Each diagram isolates one unit process. It shows its product and intermediate
flows, plus any elementary flows crossing the system boundary: extractions from
nature in green and emissions to the environment in red.

### P1 — Oil extraction

![P1 — Oil extraction](p1.svg)

### P2 — Polyester fiber production

![P2 — Polyester fiber production](p2.svg)

### P3 — T-shirt assembly

![P3 — T-shirt assembly](p3.svg)

## Scaled supply-chain diagram

![Scaled supply-chain diagram](scaled.svg)

This version adds the flow amounts and the process scaling factors (`s_1`,
`s_2`, and so on) used to produce the functional unit. Those factors are used
in the inventory and LCIA calculations below.

## Process scaling

T-shirt assembly runs once and consumes 0.2 kg of polyester fiber. Producing
that fiber consumes 1.5 kg of crude oil per kg of fiber.

```text
s_tshirt = s_3 = 1.0
s_fiber  = s_2 = s_3 × 0.2       = 0.2
s_oil    = s_1 = s_2 × 1.5       = 0.3
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
