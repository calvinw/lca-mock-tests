import os
import sys
import uuid
from pathlib import Path

import olca_schema as o
from olca_schema import units


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from ld_dir import write_ld_dir


CASE_DIR = Path(__file__).resolve().parent
NAMESPACE = uuid.UUID("f02c1ce5-d43c-49f8-a856-688c20e661fd")
LAST_CHANGE = "2026-07-20T00:00:00Z"


def uid(name):
    return str(uuid.uuid5(NAMESPACE, name))


UNIT_KINDS = {
    symbol: {
        "unit": units.unit_ref(symbol),
        "property": units.property_ref(symbol),
    }
    for symbol in ("kg", "kWh", "tkm", "unit")
}


def flow_property_factor(kind):
    return o.FlowPropertyFactor(
        conversion_factor=1.0,
        flow_property=kind["property"],
        is_ref_flow_property=True,
    )


def make_product_flow(name, symbol):
    return o.Flow(
        id=uid(f"flow:{name}"),
        last_change=LAST_CHANGE,
        name=name,
        flow_type=o.FlowType.PRODUCT_FLOW,
        category="Mock background/products",
        flow_properties=[flow_property_factor(UNIT_KINDS[symbol])],
    )


def make_elementary_flow(name):
    return o.Flow(
        id=uid(f"flow:{name}"),
        last_change=LAST_CHANGE,
        name=name,
        flow_type=o.FlowType.ELEMENTARY_FLOW,
        category="Mock background/elementary flows/air",
        flow_properties=[flow_property_factor(UNIT_KINDS["kg"])],
    )


def flow_ref(flow):
    return o.Ref(
        id=flow.id,
        ref_type=o.RefType.Flow,
        name=flow.name,
        flow_type=flow.flow_type,
    )


def process_ref(process):
    return o.Ref(
        id=process.id,
        ref_type=o.RefType.Process,
        name=process.name,
        process_type=process.process_type,
    )


def output_exchange(flow, symbol, internal_id=1):
    kind = UNIT_KINDS[symbol]
    return o.Exchange(
        flow=flow_ref(flow),
        amount=1.0,
        unit=kind["unit"],
        flow_property=kind["property"],
        internal_id=internal_id,
        is_input=False,
        is_quantitative_reference=True,
    )


def input_exchange(flow, symbol, amount, provider, internal_id):
    kind = UNIT_KINDS[symbol]
    return o.Exchange(
        flow=flow_ref(flow),
        amount=amount,
        unit=kind["unit"],
        flow_property=kind["property"],
        internal_id=internal_id,
        is_input=True,
        is_quantitative_reference=False,
        default_provider=process_ref(provider),
    )


def emission_exchange(flow, amount, internal_id):
    kind = UNIT_KINDS["kg"]
    return o.Exchange(
        flow=flow_ref(flow),
        amount=amount,
        unit=kind["unit"],
        flow_property=kind["property"],
        internal_id=internal_id,
        is_input=False,
        is_quantitative_reference=False,
    )


def make_unit_group(symbol):
    unit_ref = units.unit_ref(symbol)
    group_ref = units.group_ref(symbol)
    return o.UnitGroup(
        id=group_ref.id,
        last_change=LAST_CHANGE,
        name=group_ref.name,
        units=[
            o.Unit(
                id=unit_ref.id,
                name=unit_ref.name,
                conversion_factor=1.0,
                is_ref_unit=True,
            )
        ],
    )


mock_location = o.Location(
    id=uid("location:MOCK"),
    last_change=LAST_CHANGE,
    name="Mock location",
    code="MOCK",
)
mock_location_ref = o.Ref(
    id=mock_location.id,
    ref_type=o.RefType.Location,
    name=mock_location.name,
)

# Product and elementary flows
electricity = make_product_flow("Mock electricity, medium voltage", "kWh")
polypropylene = make_product_flow("Mock polypropylene granulate", "kg")
freight = make_product_flow("Mock freight transport", "tkm")
broom = make_product_flow("Mock plastic broom", "unit")
co2 = make_elementary_flow("Carbon dioxide, fossil")
so2 = make_elementary_flow("Sulfur dioxide")

# Reusable background unit processes
grid = o.Process(
    id=uid("process:mock-grid-electricity"),
    last_change=LAST_CHANGE,
    name="Mock grid electricity, medium voltage",
    description="Fictional unit process for cross-engine tests only.",
    category="Mock background/processes",
    process_type=o.ProcessType.UNIT_PROCESS,
    location=mock_location_ref,
    exchanges=[
        output_exchange(electricity, "kWh"),
        emission_exchange(co2, 0.4, 2),
        emission_exchange(so2, 0.0003, 3),
    ],
)

resin = o.Process(
    id=uid("process:mock-polypropylene"),
    last_change=LAST_CHANGE,
    name="Mock polypropylene granulate, at plant",
    description="Fictional unit process for cross-engine tests only.",
    category="Mock background/processes",
    process_type=o.ProcessType.UNIT_PROCESS,
    location=mock_location_ref,
    exchanges=[
        output_exchange(polypropylene, "kg"),
        input_exchange(electricity, "kWh", 2.0, grid, 2),
        emission_exchange(co2, 1.0, 3),
        emission_exchange(so2, 0.0005, 4),
    ],
)

truck = o.Process(
    id=uid("process:mock-small-truck"),
    last_change=LAST_CHANGE,
    name="Mock freight transport, small truck",
    description="Fictional unit process for cross-engine tests only.",
    category="Mock background/processes",
    process_type=o.ProcessType.UNIT_PROCESS,
    location=mock_location_ref,
    exchanges=[
        output_exchange(freight, "tkm"),
        input_exchange(electricity, "kWh", 0.08, grid, 2),
        emission_exchange(co2, 0.09, 3),
        emission_exchange(so2, 0.0001, 4),
    ],
)

# Foreground seed used to make the complete openLCA product system
assembly = o.Process(
    id=uid("process:mock-plastic-broom-assembly"),
    last_change=LAST_CHANGE,
    name="Mock plastic broom assembly",
    description=(
        "Foreground process consuming two activities from the tiny mock "
        "background. Fictional data for cross-engine tests only."
    ),
    category="Mock examples/processes",
    process_type=o.ProcessType.UNIT_PROCESS,
    location=mock_location_ref,
    exchanges=[
        output_exchange(broom, "unit"),
        input_exchange(polypropylene, "kg", 0.52, resin, 2),
        input_exchange(freight, "tkm", 0.1055, truck, 3),
    ],
)

processes = [grid, resin, truck, assembly]
links = [
    (grid, electricity, resin, 2),
    (grid, electricity, truck, 2),
    (resin, polypropylene, assembly, 2),
    (truck, freight, assembly, 3),
]
product_system = o.ProductSystem(
    id=uid("product-system:mock-plastic-broom"),
    last_change=LAST_CHANGE,
    name="Mock plastic broom product system",
    description="Pre-linked, deterministic product system for one mock broom.",
    ref_process=process_ref(assembly),
    ref_exchange=o.ExchangeRef(internal_id=1),
    target_amount=1.0,
    target_flow_property=UNIT_KINDS["unit"]["property"],
    target_unit=UNIT_KINDS["unit"]["unit"],
    processes=[process_ref(process) for process in processes],
    process_links=[
        o.ProcessLink(
            provider=process_ref(provider),
            flow=flow_ref(flow),
            process=consumer,
            exchange=o.ExchangeRef(internal_id=exchange_id),
        )
        for provider, flow, consumer, exchange_id in links
    ],
)

# Minimal EF-like subset. The CFs equal those applied to these two flows by
# the server's EF v3.1 installation, but this method is explicitly mock data.
climate = o.ImpactCategory(
    id=uid("impact:climate-change"),
    last_change=LAST_CHANGE,
    name="climate change | global warming potential (GWP100)",
    ref_unit="kg CO2-Eq",
    description="Mock subset for deterministic engine comparison.",
    impact_factors=[
        o.ImpactFactor(
            flow=flow_ref(co2),
            unit=UNIT_KINDS["kg"]["unit"],
            flow_property=UNIT_KINDS["kg"]["property"],
            value=1.0,
        )
    ],
)
acidification = o.ImpactCategory(
    id=uid("impact:acidification"),
    last_change=LAST_CHANGE,
    name="acidification | accumulated exceedance (AE)",
    ref_unit="mol H+-Eq",
    description="Mock subset for deterministic engine comparison.",
    impact_factors=[
        o.ImpactFactor(
            flow=flow_ref(so2),
            unit=UNIT_KINDS["kg"]["unit"],
            flow_property=UNIT_KINDS["kg"]["property"],
            value=1.31,
        )
    ],
)
method = o.ImpactMethod(
    id=uid("method:mock-ef-v3.1-subset"),
    last_change=LAST_CHANGE,
    name="Mock EF v3.1 subset",
    description=(
        "Two-category method for cross-engine plumbing tests only; not an "
        "official EF method and not suitable for environmental claims."
    ),
    impact_categories=[
        o.Ref(
            id=category.id,
            ref_type=o.RefType.ImpactCategory,
            name=category.name,
        )
        for category in (climate, acidification)
    ],
)

entities = (
    [mock_location, electricity, polypropylene, freight, broom, co2, so2]
    + processes
    + [product_system, climate, acidification, method]
    + [make_unit_group(symbol) for symbol in UNIT_KINDS]
)
write_ld_dir(CASE_DIR / "olca_ld", entities)

print("Wrote", CASE_DIR / "olca_ld")
print("Reference process id:", assembly.id)
print("Product system id:", product_system.id)
print("Method id:", method.id)
