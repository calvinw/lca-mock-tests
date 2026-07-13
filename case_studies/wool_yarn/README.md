# Wool yarn hand calculations

This case represents the production of 1 kg of wool yarn. These calculations
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

This is the way a unit process might appear in the database: its numbers are
the exchanges for one reference run of that process. They must be adjusted for
how much of the process actually flows through the product graph. Multiply each
exchange by the matching scaling factor in the scaled diagram to obtain its
contribution to the functional-unit inventory.

### P1 — Sheep farming

![P1 — Sheep farming](p1.svg)

### P2 — Wool yarn production

![P2 — Wool yarn production](p2.svg)

## Scaled supply-chain diagram

![Scaled supply-chain diagram](scaled.svg)

This version adds the flow amounts and the process scaling factors (`s_1`,
`s_2`, and so on) used to produce the functional unit. Those factors are used
in the inventory and LCIA calculations below.

## Process scaling

Wool yarn production runs once and consumes 1.1 kg of raw wool per kg of yarn:

```text
s_yarn  = s_2 = 1.0
s_sheep = s_1 = s_2 × 1.1 = 1.1
```

## Inventory totals

```text
CO2   = (1.1 × 0.5) + (1.0 × 2.0) = 2.55 kg
CH4   = 1.1 × 0.4                 = 0.44 kg
Water = 1.0 × 30                  = 30 L
```

## LCIA results

The characterization factors match the TRACI v2.1 factors used by the
corresponding LCA MCP teaching case.

```text
GWP = (2.55 × 1) + (0.44 × 25) = 13.55 kg CO2-eq
MIR = 0.44 × 0.014379488       = 0.00632697472 kg O3-eq
```
