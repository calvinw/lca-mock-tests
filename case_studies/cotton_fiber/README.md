# Cotton fiber hand calculations

This case represents the production of 1 kg of cotton fiber. These calculations
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

### P1 — Fertilizer production

![P1 — Fertilizer production](p1.svg)

Producing 1.0 kg of N-fertilizer emits 3.5 kg of CO2 to air.

### P2 — Cotton farming

![P2 — Cotton farming](p2.svg)

Producing 1.0 kg of cotton fiber requires 0.2 kg of N-fertilizer and extracts
8,000 L of water from nature. It emits 0.8 kg of CO2, 0.015 kg of N2O, and
0.010 kg of NH3 to air.

## Scaled supply-chain diagram

![Scaled supply-chain diagram](scaled.svg)

Each amount shown here comes from a calculation of exactly how much flows
through the product graph to create one functional unit. These amounts can be
thought of as the results of a calculation that starts at the functional unit
and works backward through the product graph. The resulting process scaling
factors (`s_1`, `s_2`, and so on) are used in the inventory and LCIA
calculations below.

## Process scaling

Cotton farming produces 1 kg of cotton fiber and therefore runs once:

```text
s_cotton = s_2 = 1.0
```

Cotton farming consumes 0.2 kg of fertilizer per kg of cotton fiber:

```text
s_fertilizer = s_1 = s_2 × 0.2 = 0.2
```

## Inventory totals

```text
CO2   = (0.2 × 3.5) + (1.0 × 0.8) = 1.5 kg
N2O   = 1.0 × 0.015                 = 0.015 kg
NH3   = 1.0 × 0.010                 = 0.010 kg
Water = 1.0 × 8000                  = 8000 L
```

## LCIA results

The characterization factors match the TRACI v2.1 factors used by the
corresponding LCA MCP teaching case.

```text
GWP  = (1.5 × 1) + (0.015 × 298) = 5.97 kg CO2-eq
EP   = 0.010 × 0.1186            = 0.001186 kg N-eq
AP   = 0.010 × 1.88              = 0.0188 kg SO2-eq
PMFP = 0.010 × (1 / 15)          = 0.0006666667 kg PM2.5-eq
```
